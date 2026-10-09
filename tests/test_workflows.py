from copy import deepcopy
from pathlib import Path
import pytest
from ai_drama.core.storage import digest, write_json, read_json
from ai_drama.schemas.models import GenerationJob, FrameAsset
from ai_drama.workflow_builder.engine import build_graph, plan, inject, repair_graph, optimize_graph, api_to_visual, visual_to_api, classify
from ai_drama.validators.graph import validate_graph
from ai_drama.workflow_registry.registry import Registry


@pytest.mark.parametrize("family", ["z-image", "qwen-image"])
def test_real_recipe_tuple_validated_against_fixture(env, family):
    graph, bindings, _ = build_graph(env["nodes"], family, "text-to-image")
    assert not validate_graph(graph, env["nodes"])
    assert visual_to_api(api_to_visual(graph, env["nodes"]), env["nodes"]) == graph


def test_missing_edit_model_not_inferred_from_nodes(env):
    result = plan(env, "qwen-image-edit", "reference-editing")
    assert not result["supported"]
    assert "qwen_image_edit" in result["reason"]


@pytest.mark.parametrize("task", ["pose-control", "inpainting"])
def test_missing_control_capability_rejected(env, task):
    assert not plan(env, "z-image", task)["supported"]


def test_upscale_is_evidenced_interpolation(env):
    graph, bindings, evidence = build_graph(env["nodes"], "core", "upscale")
    assert "interpolation" in evidence and "reference" in bindings
    assert not validate_graph(graph, env["nodes"])


@pytest.mark.parametrize("mutation, expected", [
    (lambda g: g["8"]["inputs"].update(steps="eight"), "invalid INT"),
    (lambda g: g["8"]["inputs"].update(model=["missing", 0]), "dangling"),
    (lambda g: g["8"]["inputs"].update(model=["3", 0]), "port type"),
    (lambda g: g["8"]["inputs"].update(model=["1", 5]), "invalid output port"),
    (lambda g: g["7"]["inputs"].update(width=575), "align"),
    (lambda g: g["8"]["inputs"].update(cfg=-1), "out of range"),
    (lambda g: g["8"]["inputs"].update(made_up=42), "unknown input"),
    (lambda g: g["8"]["inputs"].pop("seed"), "required input missing"),
    (lambda g: g["1"]["inputs"].update(unet_name="invented.safetensors"), "unavailable choice"),
    (lambda g: g["4"]["inputs"].update(model=["4", 0]), "Cycle"),
])
def test_invalid_graph(env, bundle, mutation, expected):
    graph = deepcopy(bundle[1].api)
    mutation(graph)
    assert expected in ";".join(validate_graph(graph, env["nodes"]))


def test_parameter_injection_ten_shots_does_not_mutate_template(bundle):
    entry, definition = bundle
    before = digest(definition.api)
    for i in range(10):
        graph = inject(definition, positive=f"SHOT{i}: different character and location", seed=i)
        assert graph["5"]["inputs"]["text"] != definition.api["5"]["inputs"]["text"]
    assert digest(definition.api) == before
    assert digest(read_json(Path(entry.api_workflow_path))) == before


def test_reference_is_not_ignored(bundle):
    with pytest.raises(ValueError, match="does not support"):
        inject(bundle[1], reference="new.png")


def test_registry_cannot_activate_offline_graph(library, env, bundle):
    reg = Registry(library)
    reg.put(bundle[0])
    with pytest.raises(ValueError, match="runtime evidence"):
        reg.activate(bundle[0], env)
    assert reg.match(env, "z-image", "text-to-image", "cinematic_3d_donghua") is None


def test_failed_job_cannot_establish_runtime(library, bundle):
    job = GenerationJob(shot_id="TEST", workflow_id=bundle[0].workflow_id, model="fixture", seed=1, prompt="test", parameters={}, output_path="test.png", status="FAILED")
    with pytest.raises(ValueError):
        Registry(library).record_runtime(bundle[0], job, library/"job.json")


def test_template_tampering_is_outdated(library, env, bundle):
    entry, definition = bundle
    definition.api["5"]["inputs"]["text"] = "outside edit"
    write_json(Path(entry.api_workflow_path), definition.api)
    assert Registry(library).validate(entry, env).validation_status == "OUTDATED"


def test_optimizer_preserves_nodes_and_original(env, bundle):
    definition = bundle[1]
    original = digest(definition.api)
    graph, changes = optimize_graph(definition.api, env["nodes"])
    assert graph.keys() == definition.api.keys()
    assert graph["7"]["inputs"]["batch_size"] == 1
    assert digest(definition.api) == original
    assert not validate_graph(graph, env["nodes"])


def test_repair_default_missing_input(env, bundle):
    graph = deepcopy(bundle[1].api)
    del graph["8"]["inputs"]["steps"]
    repaired, changes = repair_graph(graph, env["nodes"])
    assert "steps" in repaired["8"]["inputs"]
    assert "steps" not in graph["8"]["inputs"]


def test_repair_does_not_guess_model(env, bundle):
    graph = deepcopy(bundle[1].api)
    graph["1"]["inputs"]["unet_name"] = "unknown_model.safetensors"
    with pytest.raises(ValueError, match="explicit patch"):
        repair_graph(graph, env["nodes"])


def test_explicit_repair_connection(env, bundle):
    graph = deepcopy(bundle[1].api)
    graph["8"]["inputs"]["model"] = ["3", 0]
    repaired, _ = repair_graph(graph, env["nodes"], [{"node": "8", "inputs": {"model": ["4", 0]}}])
    assert not validate_graph(repaired, env["nodes"])


@pytest.mark.parametrize("text,task", [("首帧", "text-to-image"), ("参考首帧生成尾帧", "reference-editing"), ("姿势控制", "pose-control"), ("局部重绘", "inpainting"), ("图片放大", "upscale")])
def test_natural_task_router(text, task):
    assert classify(text) == task
