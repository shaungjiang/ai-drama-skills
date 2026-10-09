# AI Drama Studio

以认真查阅、复用现有、主动测试、遵循规范为准。接口不明先查 /object_info 和安装源码。

- Shared logic belongs in src/ai_drama; skills guide Codex, they do not contain separate engines.
- Run .\scripts\ai-drama.ps1 and .\.venv\Scripts\python.exe -m pytest.
- ComfyUI, PyTorch, CUDA, models, nodes and original workflows are read-only except authorized API submissions and image uploads. No model downloads.
- Draft extraction is not a semantic novel adaptation. Codex creates and imports reviewed Episode JSON for professional work.
- Explicit style choice may be locked; automatic recommendations await confirmation.
- Candidate references require user approval before becoming locked identities. Production with unapproved characters is blocked; preview mode stays marked draft.
- Reuse ACTIVE compatible workflows. Only an actual successful image execution can establish runtime verification. Environment changes trigger validation, not automatic rebuilds.
- Preserve source, rejected images, jobs, prompts and workflow versions. Do not fake images or visual scores.
- Single frame is valid; last frames require an evidenced editing workflow. Ordinary img2img is not identity-preserving editing.
- Exclude machine inventories, generated assets, novels, credentials and models from public commits.
- Natural-language entry: load skills/ai-drama-director/SKILL.md, then use the shared CLI.
