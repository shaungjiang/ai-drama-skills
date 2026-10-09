from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from uuid import uuid4
from ai_drama.core.storage import digest, now, write_json


class ComfyError(RuntimeError):
    pass


class PendingJob(ComfyError):
    """Server job may still be running. Do not resubmit on timeout."""


class Client:
    def __init__(self, url="http://127.0.0.1:8188", timeout=30):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid ComfyUI URL")
        self.url = url.rstrip("/")
        self.timeout = timeout

    def request(self, path, data=None, raw=False, headers=None):
        body = json.dumps(data).encode() if data is not None else None
        request = Request(self.url + path, data=body, headers=headers or ({"Content-Type": "application/json"} if body else {}))
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read()
            return content if raw or not content else json.loads(content)
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise ComfyError(f"HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ComfyError(f"ComfyUI connection failed: {exc}") from exc

    def inspect(self, destination: Path | None = None):
        nodes = self.request("/object_info")
        stats = self.request("/system_stats")
        env = {"online": True, "url": self.url, "checked_at": now(), "nodes": nodes, "stats": stats}
        env["fingerprint"] = fingerprint(nodes, stats)
        if destination:
            write_json(destination, env)
        return env

    def queue(self):
        return self.request("/queue")

    def submit(self, graph):
        result = self.request("/prompt", {"prompt": graph, "client_id": uuid4().hex})
        if result.get("node_errors") or not result.get("prompt_id"):
            raise ComfyError(json.dumps(result, ensure_ascii=False))
        return result["prompt_id"]

    def history(self, prompt_id):
        return self.request("/history/" + prompt_id).get(prompt_id)

    def wait(self, prompt_id, timeout=1800, progress=None):
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            history = self.history(prompt_id)
            if progress:
                progress()
            if history:
                status = history.get("status", {})
                errors = [m for m in status.get("messages", []) if m[0] in {"execution_error", "execution_interrupted"}]
                if status.get("status_str") == "error" or errors:
                    raise ComfyError(json.dumps(errors or status, ensure_ascii=False))
                if status.get("completed"):
                    images = [image for output in history.get("outputs", {}).values() for image in output.get("images", []) if image.get("type") == "output"]
                    if not images:
                        raise ComfyError("Execution completed without saved output images")
                    return images
            time.sleep(2)
        raise PendingJob(f"Timed out waiting for {prompt_id}; resume this prompt_id rather than resubmit")

    def image(self, image):
        return self.request("/view?" + urlencode({k: image[k] for k in ["filename", "subfolder", "type"] if k in image}), raw=True)

    def upload(self, path: Path):
        import hashlib
        boundary = "Drama" + uuid4().hex
        content = path.read_bytes()
        # Filename is content-addressed; never overwrites a user's original input.
        name = "drama_" + hashlib.sha256(content).hexdigest()[:20] + path.suffix.lower()
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + content + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\nfalse\r\n--{boundary}--\r\n'.encode())
        req = Request(self.url + "/upload/image", body, {"Content-Type": "multipart/form-data; boundary=" + boundary})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read())
        except (HTTPError, URLError, OSError) as exc:
            raise ComfyError(f"Upload failed: {exc}") from exc
        return "/".join(filter(None, [result.get("subfolder"), result["name"]]))

    def release(self):
        if any(self.queue().get(k) for k in ["queue_running", "queue_pending"]):
            raise ComfyError("Queue is busy; cannot unload models belonging to other tasks")
        return self.request("/free", {"unload_models": True, "free_memory": True}, raw=True)


def fingerprint(nodes, stats):
    # Exclude load, timestamp, image names and free VRAM; those change per job.
    import copy
    schema = copy.deepcopy(nodes)
    if "LoadImage" in schema:
        schema["LoadImage"]["input"]["required"]["image"][0] = ["<runtime-input>"]
    system = stats.get("system", {})
    return digest({"nodes": schema, "versions": {k: system.get(k) for k in ["os", "comfyui_version", "python_version", "pytorch_version", "required_frontend_version", "comfy_package_versions"]}, "devices": [{k: d.get(k) for k in ["name", "type", "vram_total"]} for d in stats.get("devices", [])]})
