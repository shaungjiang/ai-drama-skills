from pathlib import Path
import json
from ai_drama.schemas import models

root = Path(__file__).resolve().parents[1]/"templates"
root.mkdir(exist_ok=True)
for name in ["Project", "Episode", "Character", "ImagePrompt", "GenerationJob", "WorkflowRegistryEntry"]:
    schema = getattr(models, name).model_json_schema()
    (root/("".join(("_"+c.lower()) if c.isupper() and i else c.lower() for i,c in enumerate(name))+".schema.json")).write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
