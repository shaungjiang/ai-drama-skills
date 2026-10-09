import hashlib
from pathlib import Path
from copy import deepcopy
from PIL import Image
import pytest
from ai_drama.core.storage import read_json, write_json, exclusive
from ai_drama.schemas.models import Episode, FrameAsset
from ai_drama.pipeline.demo import create_demo, cultivation, campus
from ai_drama.pipeline.production import initialize, draft_script, load_project, load_episode, storyboard, approve_character
from ai_drama.validators.production import qc, continuity
from ai_drama.exporters.doubao import export, shot_prompts
from ai_drama.style_router.router import route
from ai_drama.frame_generator.jobs import verify_asset


def test_demo_retains_key_facts_and_duration():
    episode = cultivation()
    assert sum(s.duration for s in episode.shots) == 60
    text = " ".join(s.source_excerpt + s.dialogue for s in episode.shots)
    assert all(fact in text for fact in ["十个时辰", "江轻雪", "葬天铜棺", "藏尸图", "方圆万里", "十倍"])
    assert any(s.frame_mode == "single" for s in episode.shots)
    assert any(s.frame_mode == "dual" for s in episode.shots)


def test_two_demo_styles_are_separate(library):
    first = create_demo(library, "cultivation")
    second = create_demo(library, "campus")
    assert first["style"] != second["style"]
    assert not first["images_generated"]
    assert first["qc"] == "ERROR"


def test_extract_draft_preserves_source_beats(library):
    initialize(library, library/"examples"/"cultivation_source.txt", "test", style="cinematic_3d_donghua", confirm=True)
    episode = draft_script(library, ["林无道", "江轻雪"])
    assert episode.authoring == "extractive_draft"
    assert "方圆万里" in "".join(s.source_excerpt for s in episode.shots)
    assert not episode.characters[0].state().approved


def test_style_confirmation_gate(library):
    initialize(library, library/"examples"/"campus_source.txt", "test")
    draft_script(library)
    with pytest.raises(ValueError, match="Confirm"):
        storyboard(library)


@pytest.mark.parametrize("text,style", [("修仙宗门", "cinematic_3d_donghua"), ("大学教室", "cinematic_live_action")])
def test_router_recommends_does_not_lock(library, text, style):
    result = route(library, text)
    assert result.style_id == style and not result.confirmed and result.mode == "AUTO"


def test_explicit_style_overrides_genre(library):
    style = route(library, "修仙宗门", "cinematic_live_action", True)
    assert style.mode == "LOCKED" and style.style_id == "cinematic_live_action"


def test_draft_export_does_not_create_fake_images(library):
    demo = create_demo(library, "cultivation")
    root = Path(demo["project"])
    assert not list(root.rglob("*.png"))
    assert Path(demo["package"]).is_file()
    with pytest.raises(ValueError, match="qc PASS"):
        export(root, package=True)


def test_dual_doubao_mode_requires_explicit_capability(library):
    demo = create_demo(library, "cultivation")
    with pytest.raises(ValueError, match="Confirm"):
        export(Path(demo["project"]), mode="dual")


def test_h3_all_fields_and_natural_prompt():
    episode = cultivation()
    h3, natural = shot_prompts(episode.shots[0], episode, "single")
    assert h3.count("【") == 14
    assert "单首帧" in natural and "无敌" not in natural  # No unrelated model/API tags.


def test_invalid_reference_ids_and_duration():
    raw = cultivation().model_dump()
    raw["shots"][0]["scene_id"] = "UNKNOWN"
    with pytest.raises(ValueError):
        Episode.model_validate(raw)
    raw = cultivation().model_dump()
    raw["shots"][0]["duration"] = 7
    with pytest.raises(ValueError, match="durations"):
        Episode.model_validate(raw)


def test_axis_and_prop_discontinuity_reported():
    episode = cultivation()
    episode.shots[0].continuity_out = {"right_hand": "empty"}
    episode.shots[1].continuity_in = {"right_hand": "scroll"}
    episode.shots[1].axis_side = "B"
    issues = continuity(episode)
    assert {i.category for i in issues} >= {"axis", "state"}


def test_human_reference_approval_preserves_original(library):
    demo = create_demo(library, "cultivation")
    source = library/"synthetic_test_reference.png"
    Image.new("RGB", (32, 48), "red").save(source)
    before = source.read_bytes()
    character = approve_character(Path(demo["project"]), "EP01", "CHAR001", source, "test-only synthetic approval, not live artwork")
    assert character.state().approved
    assert source.read_bytes() == before
    assert Path(character.state().reference_images[0]) != source


def test_asset_integrity_detects_corruption(library):
    path = library/"synthetic_fixture.png"
    Image.new("RGB", (32, 48), "red").save(path)
    asset = FrameAsset(shot_id="TEST", frame="first", path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), width=32, height=48, job_id="synthetic")
    assert verify_asset(asset)
    path.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="changed"):
        verify_asset(asset)


def test_qc_refuses_missing_generated_files(library):
    result = create_demo(library, "cultivation")
    report = qc(Path(result["project"]))
    assert report.status == "ERROR"
    assert any(i.category == "asset" for i in report.issues)
    assert "No automatic" in report.visual_scoring


def test_serial_lock_rejects_parallel_producer(library):
    with exclusive(library/"production.lock"):
        with pytest.raises(RuntimeError, match="Busy"):
            with exclusive(library/"production.lock"):
                pass
    assert not (library/"production.lock").exists()
