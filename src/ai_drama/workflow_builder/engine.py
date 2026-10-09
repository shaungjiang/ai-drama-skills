from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from ai_drama.core.storage import digest, read_json, write_json, write_text, uid
from ai_drama.schemas.models import WorkflowDefinition, WorkflowRegistryEntry
from ai_drama.validators.graph import validate_graph, api_to_visual, visual_to_api, is_link
from ai_drama.workflow_builder.adapters import RECIPES

STYLES = ["cinematic_3d_donghua", "cinematic_live_action"]
TASK_ALIASES = {"character": "text-to-image", "scene": "text-to-image", "cinematic-donghua": "text-to-image", "cinematic-live-action": "text-to-image", "first-frame": "text-to-image", "last-frame": "reference-editing"}


def classify(text):
    lowered = text.lower()
    if any(word in lowered for word in ["尾帧", "参考图", "编辑", "last", "edit"]):
        return "reference-editing"
    if any(word in lowered for word in ["姿势", "pose", "controlnet"]):
        return "pose-control"
    if any(word in lowered for word in ["重绘", "inpaint"]):
        return "inpainting"
    if any(word in lowered for word in ["放大", "upscale"]):
        return "upscale"
    return "text-to-image"


def plan(env, family, task, request=""):
    task = TASK_ALIASES.get(task, task)
    family = family or ("qwen-image-edit" if task == "reference-editing" else "z-image")
    if request and "qwen" in request.lower() and not family.startswith("qwen"):
        family = "qwen-image-edit" if task == "reference-editing" else "qwen-image"
    try:
        graph, bindings, evidence = build_graph(env["nodes"], family, task)
        return {"supported": True, "family": family, "task": task, "reason": "Recipe verified against actual object_info choices and port definitions", "evidence": evidence, "nodes": sorted({n["class_type"] for n in graph.values()}), "parameters": {"width": 576, "height": 1024, "batch_size": 1}, "vram_tested": False}
    except ValueError as exc:
        return {"supported": False, "family": family, "task": task, "reason": str(exc), "required_action": "Import an installed compatible API workflow with capability evidence; do not install models automatically"}


def build_graph(nodes, family, task):
    task = TASK_ALIASES.get(task, task)
    if task not in {"text-to-image", "reference-editing", "upscale"}:
        raise ValueError(f"{task}: needs an installed verified control/inpainting recipe; use workflow import with bindings and evidence")
    if task == "upscale":
        graph = {"1": {"class_type": "LoadImage", "inputs": {"image": "drama_input.png"}}, "2": {"class_type": "ImageScale", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "width": 1152, "height": 2048, "crop": "disabled"}}, "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "AI_Drama/upscale"}}}
        errors = validate_graph(graph, nodes)
        if errors:
            raise ValueError("; ".join(errors))
        return graph, {"reference": [["1", "image"]], "width": [["2", "width"]], "height": [["2", "height"]], "output_prefix": [["3", "filename_prefix"]]}, "Core ImageScale is interpolation, not learned super-resolution"
    if family not in RECIPES:
        raise ValueError(f"No evidenced recipe for {family}; import your known working API graph")
    if task == "reference-editing" and family != "qwen-image-edit":
        raise ValueError("Ordinary text-to-image or VAE img2img does not establish reference editing capability")
    if family == "qwen-image-edit" and task != "reference-editing":
        raise ValueError("Editing recipe requires reference-editing task")
    recipe = RECIPES[family]
    # Match exact documented model tuples. Arbitrary filenames are never treated as compatible.
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": recipe["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": recipe["clip"], "type": recipe["clip_type"], "device": "cpu"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": recipe["vae"]}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": recipe["shift"]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "一座东方山门，电影构图"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "文字，水印，畸形肢体"}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 576, "height": 1024, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": 42, "steps": recipe["steps"], "cfg": recipe["cfg"], "sampler_name": recipe["sampler"], "scheduler": recipe["scheduler"], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0], "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "AI_Drama/test"}},
    }
    if family == "z-image":
        graph["6"] = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}}
    bindings = {"positive": [["5", "text"]], "seed": [["8", "seed"]], "steps": [["8", "steps"]], "width": [["7", "width"]], "height": [["7", "height"]], "output_prefix": [["10", "filename_prefix"]]}
    if family != "z-image":
        bindings["negative"] = [["6", "text"]]
    if task == "reference-editing":
        graph["11"] = {"class_type": "LoadImage", "inputs": {"image": "drama_input.png"}}
        for nid, text in [("5", "保持输入人物与场景，只让人物抬头"), ("6", "畸形，新增人物")]:
            graph[nid] = {"class_type": "TextEncodeQwenImageEdit", "inputs": {"clip": ["2", 0], "prompt": text, "vae": ["3", 0], "image": ["11", 0]}}
        bindings["positive"] = [["5", "prompt"]]
        bindings["negative"] = [["6", "prompt"]]
        bindings["reference"] = [["11", "image"]]
    errors = validate_graph(graph, nodes)
    if errors:
        raise ValueError("; ".join(errors))
    return graph, bindings, recipe["source"]


def infer_bindings(graph):
    result = {}
    for nid, node in graph.items():
        kind, inputs = node["class_type"], node["inputs"]
        if kind in {"KSampler", "KSamplerAdvanced"}:
            for name in ["seed", "steps"]:
                if name in inputs:
                    result.setdefault(name, []).append([nid, name])
            for role in ["positive", "negative"]:
                link = inputs.get(role)
                if is_link(link):
                    target = graph[link[0]]
                    name = "prompt" if "prompt" in target["inputs"] else "text"
                    if name in target["inputs"]:
                        result.setdefault(role, []).append([link[0], name])
        if kind in {"EmptyLatentImage", "EmptySD3LatentImage"}:
            for name in ["width", "height"]:
                result.setdefault(name, []).append([nid, name])
        if kind == "SaveImage":
            result.setdefault("output_prefix", []).append([nid, "filename_prefix"])
        if kind == "LoadImage":
            result.setdefault("reference", []).append([nid, "image"])
    if len(result.get("reference", [])) > 1:
        # Different characters/scenes must not silently receive the same image.
        del result["reference"]
    return result


def inject(definition, **parameters):
    graph = deepcopy(definition.api)
    for parameter, value in parameters.items():
        if value is None:
            continue
        if parameter not in definition.bindings:
            if parameter == "negative":
                continue  # Distilled Z-Image CFG=1 ignores negative conditioning.
            raise ValueError(f"Workflow does not support input: {parameter}")
        for nid, name in definition.bindings[parameter]:
            if nid not in graph or name not in graph[nid]["inputs"]:
                raise ValueError(f"Broken parameter binding {parameter}: {nid}.{name}")
            graph[nid]["inputs"][name] = value
    return graph


def save_bundle(root, env, graph, bindings, family, task, evidence, parent=None, version=1):
    errors = validate_graph(graph, env["nodes"])
    if errors:
        raise ValueError("; ".join(errors))
    wid = uid("wf")
    directory = root / "workflows" / "generated" / wid
    visual = api_to_visual(graph, env["nodes"])
    definition = WorkflowDefinition(api=graph, visual=visual, bindings=bindings)
    write_json(directory / "workflow.json", visual)
    write_json(directory / "workflow_api.json", graph)
    write_json(directory / "metadata.json", {"bindings": bindings, "capability_evidence": evidence, "created_environment": env["fingerprint"], "task_type": task, "model_family": family})
    write_text(directory / "README.md", f"# {family} / {task}\n\nImport workflow.json in ComfyUI. workflow_api.json is the separate API format.\n\nEvidence: {evidence}\n\nBatch 1; test at 576×1024. Static and environment checks passed; runtime testing is still required.\n")
    entry = WorkflowRegistryEntry(workflow_id=wid, workflow_name=f"{family}-{task}", model_family=family, model_version=next((n['inputs'].get('unet_name', '') for n in graph.values() if n['class_type'] == 'UNETLoader'), "imported"), task_type=task, supported_styles=STYLES, supported_inputs=list(bindings), required_nodes=sorted({n["class_type"] for n in graph.values()}), workflow_path=str(directory / "workflow.json"), api_workflow_path=str(directory / "workflow_api.json"), metadata_path=str(directory / "metadata.json"), validation_status="ENV_VALIDATED", environment_fingerprint=env["fingerprint"], graph_hash=digest(graph), parent_id=parent, version=version)
    return entry, definition


def load_definition(entry):
    return WorkflowDefinition(api=read_json(Path(entry.api_workflow_path)), visual=read_json(Path(entry.workflow_path)), bindings=read_json(Path(entry.metadata_path))["bindings"])


def import_graph(path, env, task, evidence=None):
    raw = read_json(path)
    graph = visual_to_api(raw, env["nodes"]) if "nodes" in raw else raw
    errors = validate_graph(graph, env["nodes"])
    if errors:
        raise ValueError("; ".join(errors))
    if task in {"reference-editing", "pose-control", "inpainting"} and not evidence:
        raise ValueError("Advanced imports require a documented capability evidence file (model version, task and reference wiring)")
    if task in {"reference-editing", "pose-control", "inpainting"}:
        if not isinstance(evidence, dict) or evidence.get("task_type") != task or not evidence.get("source") or not evidence.get("model_files") or not evidence.get("reference_nodes"):
            raise ValueError("Capability evidence requires task_type, source, model_files, reference_nodes")
        installed_files = {value for n in graph.values() for name, value in n['inputs'].items() if name.endswith('_name') and isinstance(value, str)}
        if not set(evidence['model_files']) <= installed_files:
            raise ValueError("Evidence models are not loaded by this graph")
        for nid in evidence['reference_nodes']:
            if str(nid) not in graph or graph[str(nid)]['class_type'] != 'LoadImage':
                raise ValueError("Reference evidence must identify real LoadImage nodes")
        if task == 'reference-editing':
            ordinary = {RECIPES[f]['unet'] for f in ['z-image', 'qwen-image']}
            if ordinary & installed_files:
                raise ValueError("Ordinary Qwen/Z-Image generation model cannot be declared identity editing via metadata")
    return graph, infer_bindings(graph)


def repair_graph(graph, nodes, patch=None):
    """Conservative repairs. Never guess a model family, node alias or connection."""
    graph = deepcopy(graph)
    changes = []
    for nid, node in graph.items():
        if node["class_type"] not in nodes:
            continue
        for name, spec in nodes[node["class_type"]]["input"].get("required", {}).items():
            opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            value = node["inputs"].get(name)
            if name not in node["inputs"] and "default" in opts:
                node["inputs"][name] = opts["default"]
                changes.append(f"{nid}.{name}: default restored")
            elif isinstance(spec[0], list) and isinstance(value, str) and value not in spec[0] and name.endswith("_name"):
                matches = [option for option in spec[0] if isinstance(option, str) and option.replace('\\', '/').split('/')[-1] == value.replace('\\', '/').split('/')[-1]]
                if len(matches) == 1:
                    node["inputs"][name] = matches[0]
                    changes.append(f"{nid}.{name}: unique exact basename resolved")
    if patch:
        for item in patch:
            nid = str(item["node"])
            if nid not in graph:
                raise ValueError("Patch targets unknown node")
            if "class_type" in item:
                graph[nid]["class_type"] = item["class_type"]
            graph[nid]["inputs"].update(item.get("inputs", {}))
            changes.append(f"{nid}: explicit repair applied")
    errors = validate_graph(graph, nodes)
    if errors:
        raise ValueError("Unresolved errors require an explicit patch: " + "; ".join(errors))
    return graph, changes


def optimize_graph(graph, nodes):
    graph = deepcopy(graph)
    changes = []
    for nid, node in graph.items():
        inputs = node["inputs"]
        if "batch_size" in inputs:
            inputs["batch_size"] = 1
            changes.append(f"{nid}: batch=1")
        if node["class_type"] in {"EmptyLatentImage", "EmptySD3LatentImage"}:
            inputs.update(width=576, height=1024)
            changes.append(f"{nid}: test resolution 576x1024")
        spec = nodes.get(node["class_type"], {}).get("input", {}).get("optional", {}).get("device", [])
        if node["class_type"] == "CLIPLoader" and spec and "cpu" in spec[0]:
            inputs["device"] = "cpu"
            changes.append(f"{nid}: text encoder on CPU")
    return graph, changes
