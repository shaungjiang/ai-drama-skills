from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
import yaml
from ai_drama.core.storage import read_json, write_json, write_text, digest, uid
from ai_drama.comfyui.client import Client
from ai_drama.schemas.models import Episode, Character, GenerationJob, ImagePrompt, FrameAsset
from ai_drama.pipeline.production import initialize, analyze, draft_script, import_episode, load_project, load_episode, save_episode, project_path, episode_path, storyboard, approve_character, prompt_for, status
from ai_drama.style_router.router import route
from ai_drama.workflow_registry.registry import Registry
from ai_drama.workflow_builder.engine import plan, classify, build_graph, save_bundle, load_definition, import_graph, repair_graph, optimize_graph, TASK_ALIASES, infer_bindings
from ai_drama.validators.graph import validate_graph
from ai_drama.validators.production import qc
from ai_drama.frame_generator.jobs import execute, verify_asset
from ai_drama.exporters.doubao import export

TOOL_ROOT = Path(__file__).resolve().parents[3]


def parser():
    p = argparse.ArgumentParser(prog="ai-drama", description="AI Drama Studio 2.0 — Codex planning and verified image production")
    p.add_argument("--project", type=Path, default=TOOL_ROOT, help="Production project directory")
    p.add_argument("--library", type=Path, default=TOOL_ROOT, help="Shared workflow/config library")
    p.add_argument("--url", default=None, help="ComfyUI URL (or COMFYUI_URL)")
    p.add_argument("--snapshot", type=Path, help="Offline environment snapshot; cannot prove runtime generation")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--source", type=Path, required=True)
    init.add_argument("--name", default="AI Drama Studio")
    init.add_argument("--duration", type=float, default=60)
    init.add_argument("--aspect", choices=["9:16", "16:9", "1:1"], default="9:16")
    init.add_argument("--style", choices=["cinematic_3d_donghua", "cinematic_live_action"])
    init.add_argument("--confirm-style", action="store_true", help="Use only for the user's explicit style choice")
    a = sub.add_parser("analyze")
    a.add_argument("--names", nargs="*")
    s = sub.add_parser("script")
    s.add_argument("--import", dest="import_path", type=Path)
    s.add_argument("--reviewed", action="store_true")
    s.add_argument("--names", nargs="*")
    s.add_argument("--episode", default="EP01")
    c = sub.add_parser("characters")
    c.add_argument("action", choices=["list", "import", "approve", "generate"], nargs="?", default="list")
    c.add_argument("--file", type=Path)
    c.add_argument("--id")
    c.add_argument("--reference", type=Path)
    c.add_argument("--note", default="")
    c.add_argument("--episode", default="EP01")
    c.add_argument("--view", choices=["front", "full", "side", "expression"], default="front")
    c.add_argument("--family", default="z-image")
    c.add_argument("--timeout", type=int, default=1800)
    l = sub.add_parser("locations")
    l.add_argument("action", choices=["list", "generate"])
    l.add_argument("--id")
    l.add_argument("--episode", default="EP01")
    l.add_argument("--family", default="z-image")
    l.add_argument("--timeout", type=int, default=1800)
    b = sub.add_parser("storyboard")
    b.add_argument("--episode", default="EP01")
    b.add_argument("--family", default="z-image")
    b.add_argument("--prompts", type=Path, help="Optional reviewed ImagePrompt list, supports zh/en")
    st = sub.add_parser("style").add_subparsers(dest="action", required=True)
    st.add_parser("detect")
    set_style = st.add_parser("set")
    set_style.add_argument("style", choices=["cinematic_3d_donghua", "cinematic_live_action"])
    set_style.add_argument("--confirm", action="store_true")
    comp = sub.add_parser("comfyui").add_subparsers(dest="action", required=True)
    check = comp.add_parser("check")
    check.add_argument("--save", type=Path)
    check.add_argument("--model-dir", type=Path, action="append", default=[])
    wf = sub.add_parser("workflow").add_subparsers(dest="action", required=True)
    for name in ["inspect", "plan", "match", "create", "import", "validate", "test", "repair", "optimize", "activate", "disable", "list"]:
        command = wf.add_parser(name)
        if name == "inspect":
            command.add_argument("--directory", type=Path, action="append", default=[])
        if name in {"plan", "match", "create", "import"}:
            command.add_argument("--family", default="z-image")
            command.add_argument("--task", default="text-to-image", choices=["text-to-image", "character", "scene", "cinematic-donghua", "cinematic-live-action", "reference-editing", "first-frame", "last-frame", "pose-control", "inpainting", "upscale"])
            command.add_argument("--request", default="")
            command.add_argument("--style", default="cinematic_3d_donghua")
        if name == "import":
            command.add_argument("--file", type=Path, required=True)
            command.add_argument("--evidence", type=Path)
            command.add_argument("--bindings", type=Path)
        if name in {"validate", "test", "repair", "optimize", "activate", "disable"}:
            command.add_argument("--id", required=True)
        if name == "repair":
            command.add_argument("--patch", type=Path)
        if name == "test":
            command.add_argument("--prompt", default="东方仙山山门，3D国漫电影，层次清晰，晨光，无人物，无文字")
            command.add_argument("--reference", type=Path)
            command.add_argument("--timeout", type=int, default=1800)
    fr = sub.add_parser("frames").add_subparsers(dest="action", required=True)
    for name in ["first", "last", "validate", "review"]:
        command = fr.add_parser(name)
        command.add_argument("--episode", default="EP01")
        if name in {"first", "last"}:
            command.add_argument("--shots", nargs="*")
            command.add_argument("--family", default=None)
            command.add_argument("--preview", action="store_true", help="Unapproved identity test, never production acceptance")
            command.add_argument("--regenerate", action="store_true")
            command.add_argument("--timeout", type=int, default=1800)
            command.add_argument("--seed", type=int, default=42)
        if name == "review":
            command.add_argument("--shot", required=True)
            command.add_argument("--frame", choices=["first", "last"], required=True)
            command.add_argument("--result", choices=["PASS", "WARNING", "ERROR"], required=True)
            command.add_argument("--note", required=True)
            command.add_argument("--method", choices=["human", "visual-model"], default="human")
    db = sub.add_parser("doubao").add_subparsers(dest="action", required=True)
    db_export = db.add_parser("export")
    db_export.add_argument("--episode", default="EP01")
    db_export.add_argument("--mode", choices=["single", "dual"], default="single")
    db_export.add_argument("--dual-confirmed", action="store_true")
    db_export.add_argument("--package", action="store_true")
    db_export.add_argument("--draft", action="store_true")
    for name in ["status", "qc"]:
        command = sub.add_parser(name)
        command.add_argument("--episode", default="EP01")
    jobs = sub.add_parser("jobs").add_subparsers(dest="action", required=True)
    jobs.add_parser("list")
    resume = jobs.add_parser("resume")
    resume.add_argument("--job", type=Path, required=True)
    resume.add_argument("--timeout", type=int, default=1800)
    demo = sub.add_parser("demo")
    demo.add_argument("--kind", choices=["cultivation", "campus"], default="cultivation")
    demo.add_argument("--destination", type=Path)
    return p


def client_for(args):
    config = yaml.safe_load((args.library/"config"/"comfyui.yaml").read_text(encoding="utf-8"))
    return Client(args.url or os.environ.get("COMFYUI_URL") or config["url"])


def environment(args):
    if args.snapshot:
        value = read_json(args.snapshot)
        if "nodes" not in value or "fingerprint" not in value:
            raise ValueError("Snapshot needs nodes/stats/fingerprint from comfyui check --save")
        return value
    return client_for(args).inspect(args.library/"docs"/"environment"/"latest.json")


def online_only(args):
    if args.snapshot:
        raise ValueError("Runtime actions cannot use an offline snapshot")


def create_workflow(args, env, family, task):
    graph, bindings, evidence = build_graph(env["nodes"], family, task)
    entry, _ = save_bundle(args.library, env, graph, bindings, family, TASK_ALIASES.get(task, task), evidence)
    Registry(args.library).put(entry)
    return entry


def ensure_workflow(args, env, family, task, style):
    registry = Registry(args.library)
    matched = registry.match(env, family, task, style)
    if matched:
        return matched
    # Reuse not-yet-verified structural candidates for one runtime test before batch.
    for candidate in registry.entries():
        if candidate.model_family == family and candidate.task_type == task and candidate.validation_status in {"ENV_VALIDATED", "RUNTIME_VERIFIED"}:
            candidate = registry.validate(candidate, env)
            if not candidate.validation_errors:
                return candidate
    return create_workflow(args, env, family, task)


def record_asset(project_root, episode_id, shot_id, frame, job, preview=False, source_hash=None):
    directory = episode_path(project_root, episode_id)/"shots"/shot_id
    path = directory/"metadata.json"
    data = read_json(path) if path.exists() else {"shot_id": shot_id, "assets": {}, "history": []}
    if frame in data["assets"]:
        data["history"].append(data["assets"][frame])
    data["assets"][frame] = job.assets[0].model_dump()
    data["preview"] = preview
    data.setdefault("previews", {})[frame] = preview
    data["workflow_id"] = job.workflow_id
    data["prompt_id"] = job.prompt_id
    data["parameters"] = job.parameters
    data.setdefault("source_hashes", {})[frame] = source_hash
    write_json(path, data)


def generate_frames(args):
    online_only(args)
    project, episode = load_project(args.project), load_episode(args.project, args.episode)
    if not project.style.confirmed:
        raise ValueError("Style must be confirmed")
    env, client, registry = environment(args), client_for(args), Registry(args.library)
    family = args.family or ("qwen-image-edit" if args.action == "last" else "z-image")
    task = "reference-editing" if args.action == "last" else "text-to-image"
    selected = [s for s in episode.shots if not args.shots or s.shot_id in args.shots]
    if args.shots and set(args.shots) != {s.shot_id for s in selected}:
        raise ValueError("Unknown shot IDs")
    if args.action == "last":
        selected = [s for s in selected if s.frame_mode == "dual"]
    entry = ensure_workflow(args, env, family, task, project.style.style_id)
    results = []
    for shot in selected:
        directory = episode_path(args.project, args.episode)/"shots"/shot.shot_id
        frame = args.action
        output = directory/(frame + "_frame.png")
        existing = directory/"metadata.json"
        current_prompt = prompt_for(project, episode, shot, family, frame)
        if existing.exists() and frame in read_json(existing).get("assets", {}) and not args.regenerate:
            metadata = read_json(existing)
            if metadata.get("source_hashes", {}).get(frame) != current_prompt.source_hash:
                raise ValueError("Existing frame belongs to previous script/style/bible revision; regenerate after storyboard review")
            if metadata.get("preview") and not args.preview:
                raise ValueError("Existing frame is an unapproved preview; review identity and regenerate production assets")
            verify_asset(FrameAsset.model_validate(read_json(existing)["assets"][frame]))
            results.append({"shot": shot.shot_id, "reused_asset": True})
            continue
        if not args.preview:
            if episode.authoring == "extractive_draft":
                raise ValueError("Director review required before production")
            for cid in shot.characters:
                character = next(c for c in episode.characters if c.character_id == cid)
                if not character.state().approved:
                    raise ValueError(f"Approve {character.name} reference first; --preview is explicitly unapproved")
                if task == "text-to-image" and "reference" not in entry.supported_inputs:
                    if "reference_" + cid not in entry.supported_inputs:
                        raise ValueError("Text-to-image recipe cannot consume identity references; use --preview, or import a verified reference-conditioned first-frame workflow")
        reference = None
        references = {}
        if frame == "first" and not args.preview:
            for cid in shot.characters:
                character = next(c for c in episode.characters if c.character_id == cid)
                version = shot.state_versions.get(cid, character.active_state)
                state = next(s for s in character.states if s.version == version)
                if not state.approved or not state.reference_images:
                    raise ValueError("Requested character state lacks approved reference images")
                key = "reference_" + cid
                if key in entry.supported_inputs:
                    references[key] = state.reference_images[0]
                elif len(shot.characters) == 1 and "reference" in entry.supported_inputs:
                    reference = Path(state.reference_images[0])
                else:
                    raise ValueError("Multiple characters require explicit reference_CHARxxx bindings; cannot share one reference image")
        if frame == "last":
            if not existing.exists() or "first" not in read_json(existing).get("assets", {}):
                raise ValueError("Generate first frame before editing last frame")
            asset = FrameAsset.model_validate(read_json(existing)["assets"]["first"])
            verify_asset(asset)
            if not args.preview and asset.visual_review != "PASS":
                raise ValueError("First frame requires human PASS before tail editing")
            reference = Path(asset.path)
        prompt_path = directory/(frame + "_prompt.json")
        prompt = ImagePrompt.model_validate(read_json(prompt_path)) if prompt_path.exists() else prompt_for(project, episode, shot, family, frame)
        if prompt.source_hash != current_prompt.source_hash:
            raise ValueError("Prompt is stale after script/style/bible change. Rerun storyboard and review.")
        width, height = {"9:16": (576, 1024), "16:9": (1024, 576), "1:1": (768, 768)}[project.aspect_ratio]
        print(f"Generating {shot.shot_id}/{frame} with reusable {entry.workflow_id}", file=sys.stderr, flush=True)
        job, job_path = execute(args.library, entry, client, env, output, prompt.positive, negative=prompt.negative, seed=args.seed+episode.shots.index(shot), frame=frame, shot_id=shot.shot_id, reference=reference, references=references, width=width, height=height, timeout=args.timeout, context={"project": str(args.project), "episode": args.episode, "preview": args.preview, "source_hash": prompt.source_hash})
        record_asset(args.project, args.episode, shot.shot_id, frame, job, args.preview, prompt.source_hash)
        if not entry.runtime_verified:
            entry = registry.record_runtime(entry, job, job_path)
            entry = registry.activate(entry, env)
        results.append({"shot": shot.shot_id, "job": job.job_id, "workflow": entry.workflow_id, "path": job.output_path})
    return results


def run(args):
    root = args.project
    if args.command == "init":
        if root != args.library:
            shutil.copytree(args.library/"config", root/"config", dirs_exist_ok=True)
        return initialize(root, args.source, args.name, args.duration, args.aspect, args.style, args.confirm_style)
    if args.command == "analyze":
        return analyze(root, args.names)
    if args.command == "script":
        return import_episode(root, args.import_path, args.reviewed) if args.import_path else draft_script(root, args.names, args.episode)
    if args.command == "characters":
        episode = load_episode(root, args.episode)
        if args.action == "list":
            return episode.characters
        if args.action == "import":
            if not args.file:
                raise ValueError("--file is required")
            episode.characters = [Character.model_validate(c) for c in read_json(args.file)]
            Episode.model_validate(episode.model_dump())
            save_episode(root, episode)
            return episode.characters
        if args.action == "approve":
            if not args.id or not args.reference or not args.note:
                raise ValueError("approve requires --id --reference --note (human approval evidence)")
            return approve_character(root, args.episode, args.id, args.reference, args.note)
        online_only(args)
        project, env = load_project(root), environment(args)
        if not project.style.confirmed:
            raise ValueError("Style must be confirmed before reference generation")
        char = next((c for c in episode.characters if c.character_id == args.id), None)
        if not char:
            raise ValueError("--id must name a character")
        state = char.state()
        views = {"front": "正面半身定妆，正视镜头", "full": "全身定妆，头顶与脚完整入画，站立中性姿态", "side": "左侧面定妆，保持脸部比例", "expression": "同一人物轻微坚定表情，单人单画面"}
        positive = "。".join([project.style.rules["image_style"], project.style.rules.get("character", ""), char.name + "，" + char.age + "，" + char.appearance, char.face_shape + "，" + char.facial_features + "，" + char.hairstyle + "，" + char.hair_color + "，" + char.skin_color, state.clothing, "、".join(char.visual_anchors), views[args.view], project.style.rules.get("lighting", ""), "简洁深灰背景，面部与衣装清楚可辨，无遮挡，不生成文字"])
        entry = ensure_workflow(args, env, args.family, "text-to-image", project.style.style_id)
        output = episode_path(root, args.episode)/"character_refs"/(char.character_id+"_"+args.view+"_"+uid("candidate")+".png")
        job, path = execute(args.library, entry, client_for(args), env, output, positive, frame="character", shot_id=char.character_id, timeout=args.timeout)
        if not entry.runtime_verified:
            reg = Registry(args.library)
            reg.activate(reg.record_runtime(entry, job, path), env)
        return {"candidate": str(output), "approved": False, "note": "Independent views are candidates; identity matching requires reference capability and human approval"}
    if args.command == "locations":
        episode = load_episode(root, args.episode)
        if args.action == "list":
            return episode.locations
        online_only(args)
        location = next((l for l in episode.locations if l.location_id == args.id), None)
        if not location:
            raise ValueError("Unknown location --id")
        project, env = load_project(root), environment(args)
        if not project.style.confirmed:
            raise ValueError("Lock style before scene references")
        entry = ensure_workflow(args, env, args.family, "text-to-image", project.style.style_id)
        output = episode_path(root, args.episode)/"location_refs"/(location.location_id+"_"+uid("candidate")+".png")
        prompt = "。".join([project.style.rules["image_style"], location.name, location.layout, location.architecture, "、".join(location.visual_anchors), "空间全景，布局可读，无人物，无文字"])
        job, path = execute(args.library, entry, client_for(args), env, output, prompt, frame="location", shot_id=location.location_id, timeout=args.timeout)
        if not entry.runtime_verified:
            reg = Registry(args.library)
            reg.activate(reg.record_runtime(entry, job, path), env)
        location.reference_images.append(str(output.resolve()))
        save_episode(root, episode)
        return job
    if args.command == "storyboard":
        result = storyboard(root, args.episode, args.family)
        if args.prompts:
            known = {s.shot_id: s for s in result}
            for raw in read_json(args.prompts):
                prompt = ImagePrompt.model_validate(raw)
                if prompt.shot_id not in known:
                    raise ValueError("Imported prompt has unknown shot")
                directory = episode_path(root, args.episode)/"shots"/prompt.shot_id
                write_json(directory/(prompt.frame+"_prompt.json"), prompt)
                write_text(directory/"image_prompt.txt", prompt.positive + "\n\nNegative: " + prompt.negative)
        return result
    if args.command == "style":
        project = load_project(root)
        if args.action == "detect":
            return route(args.library, Path(project.source_path).read_text(encoding="utf-8"))
        project.style = route(args.library, "", args.style, args.confirm)
        write_json(project_path(root), project)
        for episode_id in project.episodes:
            write_json(episode_path(root, episode_id)/"visual_style"/"style_bible.json", project.style)
        return project.style
    if args.command == "comfyui":
        env = environment(args)
        if args.save:
            write_json(args.save, env)
        files = []
        for directory in args.model_dir:
            directory = directory.resolve(strict=True)
            for file in directory.rglob("*"):
                if file.is_file() and file.suffix in {".safetensors", ".gguf", ".ckpt"} and file.resolve().is_relative_to(directory):
                    files.append({"path": str(file), "bytes": file.stat().st_size})
        return {"online": not bool(args.snapshot), "fingerprint": env["fingerprint"], "nodes": len(env["nodes"]), "stats": env["stats"], "models_in_authorized_directories": files, "plans": [plan(env, f, "reference-editing" if f.endswith("edit") else "text-to-image") for f in ["z-image", "qwen-image", "qwen-image-edit"]]}
    if args.command == "workflow":
        reg = Registry(args.library)
        if args.action == "list":
            return reg.entries()
        if args.action == "disable":
            entry = reg.get(args.id)
            entry.validation_status = "DISABLED"
            reg.put(entry)
            return entry
        env = environment(args)
        if args.action == "inspect":
            results = []
            for directory in args.directory:
                directory = directory.resolve(strict=True)
                for file in directory.rglob("*.json"):
                    if not file.resolve().is_relative_to(directory):
                        continue
                    try:
                        graph, _ = import_graph(file, env, "text-to-image")
                        results.append({"file": str(file), "conversion_supported": True, "compatible": True, "nodes": len(graph), "sha256": digest(read_json(file)), "capability": "unclassified: caller must specify task when importing"})
                    except (ValueError, KeyError, TypeError) as exc:
                        results.append({"file": str(file), "conversion_supported": False, "compatible": None, "reason": str(exc), "note": "Converter limitation is not evidence that the original workflow is broken; frontend API export may work"})
            write_json(args.library/"docs"/"environment"/"workflow_inventory.json", results)
            return results
        if args.action in {"plan", "match", "create", "import"}:
            task = classify(args.request) if args.request else TASK_ALIASES.get(args.task, args.task)
            family = args.family
            if args.request and "qwen" in args.request.lower():
                family = "qwen-image-edit" if task == "reference-editing" else "qwen-image"
            if args.action == "plan":
                return plan(env, family, task, args.request)
            if args.action == "match":
                matched = reg.match(env, family, task, args.style)
                return matched or {"match": None, "plan": plan(env, family, task), "action": "No auto rebuild: create/test explicitly or frames command can perform one bootstrap runtime test"}
            if args.action == "create":
                return create_workflow(args, env, family, task)
            evidence = read_json(args.evidence) if args.evidence else None
            graph, bindings = import_graph(args.file, env, task, evidence)
            if args.bindings:
                bindings = read_json(args.bindings)
            entry, _ = save_bundle(args.library, env, graph, bindings, family, task, {"source": str(args.file), "evidence": evidence})
            reg.put(entry)
            return entry
        entry = reg.get(args.id)
        if args.action == "validate":
            return reg.validate(entry, env)
        if args.action == "activate":
            online_only(args)
            return reg.activate(entry, env)
        if args.action == "test":
            online_only(args)
            entry = reg.validate(entry, env)
            if entry.validation_errors:
                raise ValueError("; ".join(entry.validation_errors))
            if entry.task_type in {"reference-editing", "upscale", "inpainting", "pose-control"} and not args.reference:
                raise ValueError("Workflow test requires --reference")
            output = args.library/"output"/"workflow_tests"/entry.workflow_id/(uid("test")+".png")
            job, path = execute(args.library, entry, client_for(args), env, output, args.prompt, reference=args.reference, timeout=args.timeout)
            return reg.record_runtime(entry, job, path)
        definition = load_definition(entry)
        if args.action == "repair":
            graph, changes = repair_graph(definition.api, env["nodes"], read_json(args.patch) if args.patch else None)
        else:
            graph, changes = optimize_graph(definition.api, env["nodes"])
        new, _ = save_bundle(args.library, env, graph, definition.bindings, entry.model_family, entry.task_type, {"derived_from": entry.workflow_id, "changes": changes}, entry.workflow_id, entry.version+1)
        reg.put(new)
        return {"workflow": new.model_dump(), "changes": changes, "runtime_verified": False}
    if args.command == "frames":
        if args.action == "validate":
            return qc(root, args.episode)
        if args.action == "review":
            path = episode_path(root, args.episode)/"shots"/args.shot/"metadata.json"
            from ai_drama.core.storage import safe_id
            safe_id(args.shot)
            data = read_json(path)
            asset = FrameAsset.model_validate(data["assets"][args.frame])
            verify_asset(asset)
            asset.visual_review, asset.review_note = args.result, args.note
            asset.review_method = args.method
            data["assets"][args.frame] = asset.model_dump()
            write_json(path, data)
            return asset
        return generate_frames(args)
    if args.command == "doubao":
        return export(root, args.episode, args.mode, args.dual_confirmed, args.package, args.draft)
    if args.command == "status":
        result = status(root, args.episode)
        result["production_complete"] = qc(root, args.episode, write=False).status == "PASS"
        return result
    if args.command == "qc":
        return qc(root, args.episode)
    if args.command == "jobs":
        if args.action == "list":
            return [read_json(p) for p in (args.library/"output"/"jobs").glob("*.json") if not p.name.endswith(".request.json")]
        online_only(args)
        job = GenerationJob.model_validate(read_json(args.job))
        entry = Registry(args.library).get(job.workflow_id)
        env = environment(args)
        completed, _ = execute(args.library, entry, client_for(args), env, Path(job.output_path), job.prompt, seed=job.seed, frame=job.parameters.get("frame", "first"), shot_id=job.shot_id, timeout=args.timeout, job_path=args.job)
        if job.shot_id.startswith("SHOT"):
            ep = next((e for e in load_project(root).episodes if (episode_path(root, e)/"shots"/job.shot_id) == Path(job.output_path).parent), None)
            if ep:
                context = job.parameters.get("context", {})
                record_asset(root, ep, job.shot_id, job.parameters.get("frame", "first"), completed, context.get("preview", True), context.get("source_hash"))
        return completed
    if args.command == "demo":
        from ai_drama.pipeline.demo import create_demo
        return create_demo(args.library, args.kind, args.destination)
    raise ValueError("Unsupported command")


def serialize(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value


def main(argv=None):
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    args.project, args.library = args.project.resolve(), args.library.resolve()
    try:
        result = run(args)
        print(json.dumps(serialize(result), ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print(json.dumps({"error": str(exc), "command": args.command}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
