from pathlib import Path
import yaml
from ai_drama.schemas.models import VisualStyle


def style_rules(root, style):
    path = Path(root) / "config" / "visual_styles" / (style + ".yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def route(root, text, explicit=None, confirmed=False):
    if explicit:
        choice, mode, reason = explicit, "MANUAL", "用户明确指定"
    elif any(word in text for word in ["修仙", "玄幻", "仙侠", "宗门", "铜棺"]):
        choice, mode, reason = "cinematic_3d_donghua", "AUTO", "东方奇幻叙事"
    else:
        choice, mode, reason = "cinematic_live_action", "AUTO", "现实/校园题材；如不符合请手动指定"
    return VisualStyle(style_id=choice, mode="LOCKED" if confirmed else mode, confirmed=confirmed, rules=style_rules(root, choice), reason=reason)
