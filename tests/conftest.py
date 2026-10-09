"""Offline fixtures. Synthetic images in tests never establish live runtime acceptance."""
from pathlib import Path
import shutil
import pytest
from ai_drama.core.storage import read_json, digest
from ai_drama.workflow_builder.engine import build_graph, save_bundle

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def env():
    nodes = read_json(ROOT/"tests"/"fixtures"/"object_info_subset.json")
    return {"nodes": nodes, "stats": {"system": {"comfyui_version": "fixture"}}, "fingerprint": digest(nodes)}


@pytest.fixture
def library(tmp_path):
    shutil.copytree(ROOT/"config", tmp_path/"config")
    shutil.copytree(ROOT/"examples", tmp_path/"examples")
    return tmp_path


@pytest.fixture
def bundle(library, env):
    graph, bindings, evidence = build_graph(env["nodes"], "z-image", "text-to-image")
    return save_bundle(library, env, graph, bindings, "z-image", "text-to-image", evidence)
