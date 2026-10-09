import importlib.util
from pathlib import Path
import pytest
import yaml
from ai_drama.cli.main import parser, main

ROOT = Path(__file__).resolve().parents[1]


def test_all_thirteen_skills_frontmatter_resources_and_shared_toolchain():
    directories = sorted((ROOT/"skills").iterdir())
    assert len(directories) == 13
    for directory in directories:
        text = (directory/"SKILL.md").read_text(encoding="utf-8")
        meta = yaml.safe_load(text.split("---", 2)[1])
        assert meta["name"] == directory.name
        assert meta["description"] and len(meta["name"]) < 64
        assert (directory/"references"/"shared_tools.md").is_file()
        assert "src/ai_drama" in text


@pytest.mark.parametrize("arguments", ["analyze", "script", "characters", "storyboard", "style detect", "style set cinematic_3d_donghua", "comfyui check", "workflow inspect", "workflow plan", "workflow match", "workflow create", "workflow validate --id x", "workflow test --id x", "workflow repair --id x", "workflow optimize --id x", "workflow activate --id x", "workflow disable --id x", "workflow list", "frames first", "frames last", "frames validate", "doubao export", "status", "qc"])
def test_required_command_arguments_parse(arguments):
    assert parser().parse_args(arguments.split()).command


def test_help_runs_real_cli(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--help"])
    assert result.value.code == 0
    assert "workflow" in capsys.readouterr().out


def test_installer_collision_preflight(tmp_path):
    spec = importlib.util.spec_from_file_location("install_skills", ROOT/"scripts"/"install_skills.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path/"skills"
    module.install(target)
    assert len(list(target.iterdir())) == 13
    file = target/"ai-drama-director"/"SKILL.md"
    file.write_text("user custom skill", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing overwrite"):
        module.install(target)
    assert file.read_text() == "user custom skill"
