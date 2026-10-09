from __future__ import annotations

from pathlib import Path
from ai_drama.core.storage import read_json, write_json, exclusive, digest, now
from ai_drama.schemas.models import WorkflowRegistryEntry, GenerationJob
from ai_drama.workflow_builder.engine import load_definition, TASK_ALIASES
from ai_drama.validators.graph import validate_graph


class Registry:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "workflow_registry.json"

    def entries(self):
        if not self.path.exists():
            return []
        return [WorkflowRegistryEntry.model_validate(value) for value in read_json(self.path)]

    def get(self, wid):
        for entry in self.entries():
            if entry.workflow_id == wid:
                return entry
        raise ValueError(f"Workflow not found: {wid}")

    def put(self, entry):
        with exclusive(self.path.with_suffix(".lock")):
            entries = self.entries()
            entries = [e for e in entries if e.workflow_id != entry.workflow_id] + [entry]
            write_json(self.path, [e.model_dump(mode="json") for e in entries])

    def validate(self, entry, env):
        definition = load_definition(entry)
        errors = validate_graph(definition.api)
        if errors:
            entry.validation_status = "FAILED"
        elif digest(definition.api) != entry.graph_hash:
            errors = ["Template changed outside version management; import as a new version"]
            entry.validation_status = "OUTDATED"
        else:
            entry.validation_status = "STATIC_VALIDATED"
            errors = validate_graph(definition.api, env["nodes"])
            if errors:
                entry.validation_status = "FAILED"
            else:
                entry.environment_fingerprint = env["fingerprint"]
                entry.validation_status = "ENV_VALIDATED"
                if entry.runtime_verified and entry.runtime_graph_hash == entry.graph_hash:
                    entry.validation_status = "RUNTIME_VERIFIED"
        entry.validation_errors = errors
        self.put(entry)
        return entry

    def activate(self, entry, env):
        entry = self.validate(entry, env)
        if entry.validation_errors or not entry.runtime_verified or entry.runtime_graph_hash != entry.graph_hash or not entry.evidence_job:
            raise ValueError("Activation requires successful runtime evidence for this exact graph and a compatible environment")
        evidence = GenerationJob.model_validate(read_json(Path(entry.evidence_job)))
        if evidence.status != "SUCCEEDED" or not evidence.assets:
            raise ValueError("Missing successful runtime job")
        from ai_drama.frame_generator.jobs import verify_asset
        for asset in evidence.assets:
            verify_asset(asset)
        entry.validation_status = "ACTIVE"
        self.put(entry)
        return entry

    def match(self, env, family, task, style, inputs=None):
        task = TASK_ALIASES.get(task, task)
        for entry in sorted(self.entries(), key=lambda e: e.version, reverse=True):
            if entry.validation_status != "ACTIVE" or not entry.runtime_verified:
                continue
            if family and entry.model_family != family:
                continue
            if entry.task_type != task or style not in entry.supported_styles:
                continue
            if not set(inputs or []) <= set(entry.supported_inputs):
                continue
            definition = load_definition(entry)
            if digest(definition.api) != entry.graph_hash:
                entry.validation_status = "OUTDATED"
                self.put(entry)
                continue
            if entry.environment_fingerprint != env["fingerprint"]:
                original_status = entry.validation_status
                entry = self.validate(entry, env)
                if entry.validation_errors:
                    continue
                # Recheck compatible nodes/choices; do not rebuild on environment changes.
                if original_status == "ACTIVE" and entry.runtime_verified:
                    entry = self.activate(entry, env)
            if validate_graph(definition.api, env["nodes"]):
                continue
            return entry
        return None

    def record_runtime(self, entry, job, evidence_path):
        if job.status != "SUCCEEDED" or not job.assets:
            raise ValueError("Runtime verification requires real saved images")
        entry.runtime_verified = True
        entry.runtime_graph_hash = entry.graph_hash
        entry.evidence_job = str(evidence_path.resolve())
        entry.last_tested_at = now()
        entry.validation_status = "RUNTIME_VERIFIED"
        self.put(entry)
        return entry
