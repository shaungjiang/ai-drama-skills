"""Copy skills without overwriting existing skills; default is repo-local discovery."""
import argparse
import hashlib
import shutil
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def install(target, dry_run=False):
    copied, identical = [], []
    sources = sorted((ROOT/"skills").iterdir())
    # Preflight every collision before creating any files.
    for source in sources:
        destination = target/source.name
        if destination.exists():
            for file in source.rglob("*"):
                if file.is_file():
                    existing = destination/file.relative_to(source)
                    if not existing.exists() or existing.read_bytes() != file.read_bytes():
                        raise ValueError(f"Existing skill differs, refusing overwrite: {destination}")
            identical.append(source.name)
        else:
            copied.append(source.name)
    if not dry_run:
        for source in sources:
            if source.name in copied:
                shutil.copytree(source, target/source.name)
    return {"target": str(target), "copied": copied, "identical": identical, "dry_run": dry_run, "host_loaded": False, "next": "Open a new Codex chat rooted in the project; file discovery is not proof of hot loading"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=ROOT/".agents"/"skills")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import json
    print(json.dumps(install(args.target.resolve(), args.dry_run), ensure_ascii=False, indent=2))
