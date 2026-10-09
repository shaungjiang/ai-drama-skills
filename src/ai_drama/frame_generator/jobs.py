from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import time
from pathlib import Path
from PIL import Image
from ai_drama.comfyui.client import Client, ComfyError, PendingJob
from ai_drama.core.storage import now, write_json, read_json, exclusive, uid
from ai_drama.schemas.models import GenerationJob, FrameAsset
from ai_drama.validators.graph import validate_graph
from ai_drama.workflow_builder.engine import inject, load_definition


def verify_asset(asset):
    path = Path(asset.path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != asset.sha256:
        raise ValueError(f"Asset content changed: {path}")
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        if image.size != (asset.width, asset.height):
            raise ValueError("Asset dimensions changed")
    return True


def resources(client, path):
    sample = {"timestamp": now()}
    try:
        sample["stats"] = client.request("/system_stats")
    except ComfyError as exc:
        sample["stats_error"] = str(exc)
    try:
        sample["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(sample, ensure_ascii=False) + "\n")


def execute(root, entry, client, env, output, positive, *, negative="", seed=42, frame="first", shot_id="TEST", reference=None, references=None, width=576, height=1024, timeout=1800, retry=3, job_path=None, context=None):
    """One active producer at a time. Persist prompt_id before polling; reuse on resume."""
    if retry not in range(1, 4):
        raise ValueError("Maximum retries must be between 1 and 3")
    root, output = Path(root), Path(output)
    definition = load_definition(entry)
    if reference and "reference" not in definition.bindings:
        raise ValueError("This workflow cannot consume reference images")
    references = references or {}
    if not set(references) <= set(definition.bindings):
        raise ValueError("Unknown reference parameter bindings")
    if job_path:
        job_path = Path(job_path)
        job = GenerationJob.model_validate(read_json(job_path))
        if job.workflow_id != entry.workflow_id or Path(job.output_path) != output:
            raise ValueError("Resume job does not match requested workflow/output")
        if job.status == "SUCCEEDED":
            for asset in job.assets:
                verify_asset(asset)
            return job, job_path
        if job.status == "UNKNOWN" and not job.prompt_id:
            raise ValueError("Submission outcome unknown. Inspect server queue/history and attach prompt_id; do not blindly resubmit")
        graph = read_json(job_path.with_suffix(".request.json"))
    else:
        parameters = {"positive": positive, "negative": negative, "seed": seed, "width": width, "height": height, "output_prefix": "AI_Drama/" + uid("image")}
        parameters = {k: v for k, v in parameters.items() if k in definition.bindings}
        if reference:
            parameters["reference"] = client.upload(Path(reference))
        for binding, path in references.items():
            parameters[binding] = client.upload(Path(path))
        graph = inject(definition, **parameters)
        if any(n["inputs"].get("batch_size", 1) != 1 for n in graph.values()):
            raise ValueError("Low VRAM execution requires batch_size=1")
        paths = ([str(reference)] if reference else []) + [str(path) for path in references.values()]
        job = GenerationJob(shot_id=shot_id, workflow_id=entry.workflow_id, model=entry.model_version, seed=seed, prompt=positive, parameters=parameters | {"reference_paths": paths, "frame": frame, "width": width, "height": height, "context": context or {}}, output_path=str(output.resolve()))
        job_path = root / "output" / "jobs" / (job.job_id + ".json")
        write_json(job_path, job)
        write_json(job_path.with_suffix(".request.json"), graph)
    errors = validate_graph(graph, env["nodes"])
    if errors:
        job.status, job.error = "FAILED", "; ".join(errors)
        write_json(job_path, job)
        raise ValueError(job.error)
    with exclusive(root / "output" / ".production.lock"):
        sampled_at = 0.0

        def sample():
            nonlocal sampled_at
            if time.monotonic() - sampled_at > 10:
                resources(client, job_path.with_suffix(".resources.jsonl"))
                sampled_at = time.monotonic()

        while job.attempts < retry or job.prompt_id:
            try:
                if not job.prompt_id:
                    if any(client.queue().get(k) for k in ["queue_running", "queue_pending"]):
                        raise PendingJob("ComfyUI queue is busy; retry after existing tasks finish")
                    last_model = root / "output" / "last_model.json"
                    if last_model.exists() and read_json(last_model).get("model") != entry.model_version:
                        client.release()
                    job.attempts += 1
                    job.status, job.error = "SUBMITTED", None
                    write_json(job_path, job)
                    try:
                        job.prompt_id = client.submit(graph)
                    except ComfyError:
                        # A lost HTTP response might follow an accepted request.
                        job.status = "UNKNOWN"
                        raise
                    write_json(last_model, {"model": entry.model_version})
                    write_json(job_path, job)
                job.status = "RUNNING"
                write_json(job_path, job)
                images = client.wait(job.prompt_id, timeout=timeout, progress=sample)
                assets = []
                for index, item in enumerate(images):
                    raw = client.image(item)
                    with Image.open(io.BytesIO(raw)) as image:
                        image.load()
                        if image.format != "PNG":
                            raise ComfyError("Expected PNG output from SaveImage")
                        actual_width, actual_height = image.size
                    target = output if index == 0 else output.with_stem(output.stem + f"_{index}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Keep previous successful results before regeneration.
                    if target.exists():
                        backup = target.with_name(target.stem + "." + uid("previous") + target.suffix)
                        os.replace(target, backup)
                    temporary = target.with_suffix(".png.tmp")
                    temporary.write_bytes(raw)
                    os.replace(temporary, target)
                    assets.append(FrameAsset(shot_id=shot_id, frame=frame, path=str(target.resolve()), sha256=hashlib.sha256(raw).hexdigest(), width=actual_width, height=actual_height, job_id=job.job_id, reference_paths=job.parameters.get("reference_paths", [])))
                job.assets = assets
                job.status, job.completed_at, job.error = "SUCCEEDED", now(), None
                write_json(job_path, job)
                sample()
                return job, job_path
            except PendingJob as exc:
                job.error = str(exc)
                write_json(job_path, job)
                raise
            except (ComfyError, OSError, ValueError) as exc:
                job.error = str(exc)
                if job.status == "UNKNOWN":
                    write_json(job_path, job)
                    raise
                # Retry only after the server explicitly recorded execution failure.
                explicit_failure = job.prompt_id and client.history(job.prompt_id) and client.history(job.prompt_id).get("status", {}).get("status_str") == "error"
                if not explicit_failure:
                    write_json(job_path, job)
                    raise
                job.status = "FAILED"
                if "out of memory" in str(exc).lower() or "oom" in str(exc).lower():
                    for n in graph.values():
                        if n["class_type"] in {"EmptyLatentImage", "EmptySD3LatentImage"}:
                            for axis in ["width", "height"]:
                                n["inputs"][axis] = max(256, int(n["inputs"][axis] * 0.75) // 16 * 16)
                                job.parameters[axis] = n["inputs"][axis]
                    job.parameters["oom_reduced"] = True
                    write_json(job_path.with_suffix(".request.json"), graph)
                    client.release()
                job.prompt_id = None
                write_json(job_path, job)
                if job.attempts >= retry:
                    raise
        raise ComfyError("Retry budget exhausted")
