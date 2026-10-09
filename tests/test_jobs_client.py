"""Simulated transport/job tests only; these do NOT prove real ComfyUI generation."""
import io
import json
from pathlib import Path
from PIL import Image
import pytest
from ai_drama.comfyui.client import Client, ComfyError, PendingJob, fingerprint
from ai_drama.core.storage import read_json, write_json
from ai_drama.frame_generator.jobs import execute
from ai_drama.workflow_registry.registry import Registry
from ai_drama.workflow_builder.engine import load_definition


class SimulatedClient:
    def __init__(self):
        self.submissions = 0
        self.releases = 0
        self.failures = []
        self.submitted = []

    def queue(self):
        return {"queue_running": [], "queue_pending": []}

    def submit(self, graph):
        self.submissions += 1
        self.submitted.append(graph)
        return "simulated-prompt-id"

    def wait(self, prompt_id, timeout=30, progress=None):
        if self.failures:
            raise self.failures.pop(0)
        return [{"filename": "synthetic_test_only.png", "subfolder": "", "type": "output"}]

    def image(self, result):
        stream = io.BytesIO()
        Image.new("RGB", (576, 1024), "red").save(stream, "PNG")
        return stream.getvalue()

    def history(self, prompt_id):
        return {"status": {"status_str": "error"}}

    def release(self):
        self.releases += 1


@pytest.fixture(autouse=True)
def disable_live_resource_collection(monkeypatch):
    monkeypatch.setattr("ai_drama.frame_generator.jobs.resources", lambda *args: None)


def test_success_requires_decodable_saved_image(library, env, bundle):
    client = SimulatedClient()
    job, path = execute(library, bundle[0], client, env, library/"synthetic.png", "fixture")
    assert job.status == "SUCCEEDED" and job.assets
    assert read_json(path)["prompt_id"] == "simulated-prompt-id"
    assert client.submissions == 1


def test_pending_resume_does_not_resubmit(library, env, bundle):
    client = SimulatedClient()
    client.failures = [PendingJob("server still running")]
    output = library/"synthetic.png"
    with pytest.raises(PendingJob):
        execute(library, bundle[0], client, env, output, "fixture")
    job_path = next(p for p in (library/"output"/"jobs").glob("*.json") if not p.name.endswith(".request.json"))
    assert read_json(job_path)["status"] == "RUNNING"
    execute(library, bundle[0], client, env, output, "fixture", job_path=job_path)
    assert client.submissions == 1


def test_oom_retries_preserve_template_and_reduce_resolution(library, env, bundle):
    client = SimulatedClient()
    client.failures = [ComfyError("CUDA out of memory")]
    job, _ = execute(library, bundle[0], client, env, library/"synthetic.png", "fixture")
    assert client.submissions == 2 and client.releases == 1
    assert job.parameters["oom_reduced"]
    assert job.parameters["width"] < 576
    assert load_definition(bundle[0]).api["7"]["inputs"]["width"] == 576


def test_retry_limit_is_three(library, env, bundle):
    client = SimulatedClient()
    client.failures = [ComfyError("explicit execution failed")] * 4
    with pytest.raises(ComfyError):
        execute(library, bundle[0], client, env, library/"synthetic.png", "fixture")
    assert client.submissions == 3


def test_corrupt_image_never_marks_succeeded(library, env, bundle):
    client = SimulatedClient()
    client.image = lambda _: b"corrupt image"
    with pytest.raises((ComfyError, OSError)):
        execute(library, bundle[0], client, env, library/"synthetic.png", "fixture", retry=1)
    job_path = next(p for p in (library/"output"/"jobs").glob("*.json") if not p.name.endswith(".request.json"))
    assert read_json(job_path)["status"] != "SUCCEEDED"
    assert not (library/"synthetic.png").exists()


def test_unknown_submission_not_retried(library, env, bundle):
    client = SimulatedClient()

    def submit(graph):
        client.submissions += 1
        raise ComfyError("response lost")

    client.submit = submit
    with pytest.raises(ComfyError):
        execute(library, bundle[0], client, env, library/"synthetic.png", "fixture")
    assert client.submissions == 1
    job_path = next(p for p in (library/"output"/"jobs").glob("*.json") if not p.name.endswith(".request.json"))
    assert read_json(job_path)["status"] == "UNKNOWN"
    with pytest.raises(ValueError, match="unknown"):
        execute(library, bundle[0], client, env, library/"synthetic.png", "fixture", job_path=job_path)


def test_active_registry_reuses_ten_shots_cross_styles_and_projects(library, env, bundle):
    # Synthetic evidence is intentionally confined to this tmp_path fixture.
    client = SimulatedClient()
    job, path = execute(library, bundle[0], client, env, library/"synthetic.png", "fixture")
    reg = Registry(library)
    entry = reg.record_runtime(bundle[0], job, path)
    entry = reg.activate(entry, env)
    for i in range(10):
        style = "cinematic_3d_donghua" if i % 2 == 0 else "cinematic_live_action"
        matched = reg.match(env, "z-image", "first-frame", style)
        assert matched.workflow_id == entry.workflow_id
    assert reg.match(env, "qwen-image", "text-to-image", "cinematic_live_action") is None
    assert reg.match(env, "z-image", "reference-editing", "cinematic_live_action") is None
    entry.validation_status = "DISABLED"
    reg.put(entry)
    assert reg.match(env, "z-image", "text-to-image", "cinematic_live_action") is None


def test_fingerprint_ignores_dynamic_resources_and_input_images(env):
    import copy
    nodes = copy.deepcopy(env["nodes"])
    a = fingerprint(nodes, {"system": {"ram_free": 1024}, "devices": []})
    nodes["LoadImage"]["input"]["required"]["image"][0].append("new_upload.png")
    b = fingerprint(nodes, {"system": {"ram_free": 4096}, "devices": []})
    assert a == b


def test_http_client_serializes_prompt_and_reads_response(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"prompt_id":"transport-fixture","node_errors":{}}'

    def urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr("ai_drama.comfyui.client.urlopen", urlopen)
    assert Client().submit({"1": {"class_type": "test", "inputs": {}}}) == "transport-fixture"
    assert captured["url"].endswith("/prompt")
    assert "prompt" in captured["body"] and "client_id" in captured["body"]
