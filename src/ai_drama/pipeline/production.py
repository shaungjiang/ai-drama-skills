from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from ai_drama.core.storage import read_json, write_json, write_text, digest
from ai_drama.schemas.models import Project, Episode, Character, Location, Scene, Shot, ImagePrompt
from ai_drama.style_router.router import route


def project_path(root):
    return Path(root) / "project.json"


def load_project(root):
    return Project.model_validate(read_json(project_path(root)))


def episode_path(root, episode_id="EP01"):
    from ai_drama.core.storage import safe_id
    return Path(root) / "output" / safe_id(episode_id)


def load_episode(root, episode_id="EP01"):
    return Episode.model_validate(read_json(episode_path(root, episode_id) / "episode.json"))


def initialize(root, source, name, duration=60, aspect="9:16", style=None, confirm=False):
    root, source = Path(root), Path(source)
    if project_path(root).exists():
        raise ValueError("Project exists; do not reinitialize. Create another --project directory")
    text = source.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("Source text is empty")
    copied = root / "input" / "novel.txt"
    write_text(copied, text)
    project = Project(name=name, source_path=str(copied.resolve()), source_hash=hashlib.sha256(text.encode()).hexdigest(), duration=duration, aspect_ratio=aspect, style=route(root, text, style, confirm))
    write_json(project_path(root), project)
    return project


def analyze(root, names=None):
    project = load_project(root)
    text = Path(project.source_path).read_text(encoding="utf-8")
    names = names or []
    if not names:
        names = list(dict.fromkeys(re.findall(r"(?:主角|未婚妻|男主|女主|姓名)[：:]\s*([\u4e00-\u9fff]{2,4})", text)))
    relations = []
    for line in text.splitlines():
        involved = [name for name in names if name in line]
        if len(involved) >= 2:
            relations.append({"from": involved[0], "to": involved[1], "evidence": line, "review": "requires semantic confirmation"})
    sentences = [s.strip() for s in re.split(r"(?<=[。！？.!?])|\n+", text) if s.strip()]
    data = {"source_hash": project.source_hash, "characters": names, "relationships": relations, "beats": sentences, "analysis_mode": "extractive", "review_required": True, "notes": "Only literal names/evidence are extracted. Codex must review conflict, compression, dialogue and world details."}
    write_json(Path(root) / "output" / "analysis.json", data)
    return data


def draft_script(root, names=None, episode_id="EP01"):
    project = load_project(root)
    analysis = analyze(root, names)
    cast = [Character(character_id=f"CHAR{i+1:03}", name=name) for i, name in enumerate(analysis["characters"])]
    location = Location(location_id="LOC001", name="待核对原著场景", layout="待 Codex 依据原文建立空间关系", architecture="待确认")
    scene = Scene(scene_id="SCENE001", location_id=location.location_id, characters=[c.character_id for c in cast], objective="待审阅")
    total = max(1, math.ceil(project.duration / 6))
    beats = analysis["beats"]
    # All original beats are retained in grouped blocks rather than discarded.
    groups = ["".join(beats[len(beats)*i//total:len(beats)*(i+1)//total]) or "原文停顿；待导演设计可见动作" for i in range(total)]
    shots = []
    for i, beat in enumerate(groups):
        duration = round(project.duration / total, 4) if i < total-1 else project.duration - sum(s.duration for s in shots)
        shots.append(Shot(shot_id=f"SHOT{i+1:03}", scene_id=scene.scene_id, characters=[c.character_id for c in cast if c.name in beat], duration=duration, action="待导演将原著事件改为可见动作：" + beat, first_frame="待设计：" + beat, last_frame="待设计：" + beat, source_excerpt=beat))
    episode = Episode(episode_id=episode_id, title=project.name, duration=project.duration, characters=cast, locations=[location], scenes=[scene], shots=shots, synopsis="".join(beats), hook=beats[0] if beats else "", cliffhanger=beats[-1] if beats else "")
    save_episode(root, episode)
    return episode


def import_episode(root, path, reviewed=False):
    episode = Episode.model_validate(read_json(Path(path)))
    project = load_project(root)
    if abs(episode.duration-project.duration) > 0.1:
        raise ValueError("Imported episode duration differs from project duration")
    if reviewed:
        episode.authoring = "codex_reviewed"
    save_episode(root, episode)
    return episode


def save_episode(root, episode):
    directory = episode_path(root, episode.episode_id)
    previous = directory / "episode.json"
    if previous.exists():
        from ai_drama.core.storage import uid
        write_json(directory / "revisions" / (uid("episode") + ".json"), read_json(previous))
    write_json(previous, episode)
    write_json(directory / "bible" / "characters.json", [c.model_dump() for c in episode.characters])
    write_json(directory / "bible" / "locations.json", [l.model_dump() for l in episode.locations])
    write_json(directory / "bible" / "props.json", [p.model_dump() for p in episode.props])
    write_json(directory / "storyboard" / "storyboard.json", [s.model_dump() for s in episode.shots])
    lines = [f"# {episode.title}", f"{episode.duration:g} 秒 · {episode.authoring}", f"开场：{episode.hook}", f"剧情：{episode.synopsis}"]
    for shot in episode.shots:
        lines += [f"\n## {shot.shot_id} · {shot.duration:g} 秒", f"{shot.size} / {shot.angle} / {shot.camera_movement}", f"动作：{shot.action}", f"对白：{shot.dialogue}", f"首帧：{shot.first_frame}", f"尾帧：{shot.last_frame}", f"原文证据：{shot.source_excerpt}"]
    lines += [f"\n结尾：{episode.cliffhanger}"]
    write_text(directory / "script" / "episode_script.md", "\n\n".join(lines))
    project = load_project(root)
    if episode.episode_id not in project.episodes:
        project.episodes.append(episode.episode_id)
        write_json(project_path(root), project)
    write_json(directory / "visual_style" / "style_bible.json", project.style)


def prompt_for(project, episode, shot, family="z-image", frame="first"):
    cast = {c.character_id: c for c in episode.characters}
    scene = next(s for s in episode.scenes if s.scene_id == shot.scene_id)
    location = next(l for l in episode.locations if l.location_id == scene.location_id)
    constraints = []
    for cid in shot.characters:
        c = cast[cid]
        version = shot.state_versions.get(cid, c.active_state)
        state = next(s for s in c.states if s.version == version)
        constraints.append(f"{c.name}，{c.gender}，{c.age}，{c.identity}；{c.appearance}；脸型{c.face_shape}，{c.facial_features}，{c.hairstyle}，{c.hair_color}，{c.skin_color}，{c.physique}；服装{state.clothing}；饰品{'、'.join(state.accessories)}；身份锚点{'、'.join(c.visual_anchors)}")
    props = "；".join(p.name + "：" + p.appearance for p in episode.props if p.prop_id in shot.prop_ids)
    state_description = shot.first_frame if frame == "first" else shot.last_frame
    positive = "。".join([project.style.rules["image_style"], "；".join(constraints) or "环境空镜，无人物", state_description, "表情：" + shot.expression, location.name + "，" + location.layout + "，" + location.architecture, scene.time + "，" + scene.weather + "，" + scene.lighting, project.style.rules.get("lighting", ""), shot.size + "，" + shot.angle, shot.composition, project.style.rules["composition"], "道具：" + props, "场景及角色视觉锚点保持固定，禁止新增人物，不生成字幕文字，单个瞬间的静态画面"])
    negative = "，".join(project.style.rules["avoid"] + ["文字", "水印", "额外肢体", "错误手指", "重复人物"])
    if frame == "last":
        positive = "基于输入首帧进行编辑，保留人物身份、衣服、场景布局、道具及光源方向；只按目标状态改变动作。" + positive
    return ImagePrompt(shot_id=shot.shot_id, frame=frame, positive=positive, negative=negative, model_family=family, source_hash=digest({"source": project.source_hash, "episode": episode.model_dump(), "shot": shot.model_dump(), "style": project.style.model_dump()}))


def storyboard(root, episode_id="EP01", family="z-image"):
    project, episode = load_project(root), load_episode(root, episode_id)
    if not project.style.confirmed or project.style.mode != "LOCKED":
        raise ValueError("Confirm and lock visual style before generating production prompts")
    for shot in episode.shots:
        directory = episode_path(root, episode_id) / "shots" / shot.shot_id
        prompts = [prompt_for(project, episode, shot, family)]
        if shot.frame_mode == "dual":
            prompts.append(prompt_for(project, episode, shot, family, "last"))
        for prompt in prompts:
            write_json(directory / (prompt.frame + "_prompt.json"), prompt)
        write_text(directory / "image_prompt.txt", "\n\n".join(f"{p.frame}\n正面：{p.positive}\n负面：{p.negative}" for p in prompts))
    write_json(episode_path(root, episode_id) / "storyboard" / "storyboard.json", [s.model_dump() for s in episode.shots])
    return episode.shots


def approve_character(root, episode_id, character_id, path, note):
    from PIL import Image
    import shutil
    episode = load_episode(root, episode_id)
    char = next((c for c in episode.characters if c.character_id == character_id), None)
    if not char:
        raise ValueError("Unknown character ID")
    path = Path(path).resolve()
    with Image.open(path) as image:
        image.load()
    directory = episode_path(root, episode_id) / "character_refs"
    target = directory / f"{character_id}_v{char.active_state}_{digest(str(path))[:8]}{path.suffix}"
    directory.mkdir(parents=True, exist_ok=True)
    if path != target.resolve():
        if target.exists():
            from ai_drama.core.storage import uid
            target = target.with_stem(target.stem + uid("approved"))
        shutil.copy2(path, target)
    state = char.state()
    state.reference_images = [str(target.resolve())]
    state.approved = True
    state.approval_note = note
    save_episode(root, episode)
    return char


def status(root, episode_id="EP01"):
    from ai_drama.schemas.models import GenerationJob
    project = load_project(root)
    episode = load_episode(root, episode_id)
    jobs = [GenerationJob.model_validate(read_json(p)) for p in (Path(root)/"output"/"jobs").glob("*.json") if not p.name.endswith(".request.json")]
    firsts = 0
    for shot in episode.shots:
        metadata = episode_path(root, episode_id) / "shots" / shot.shot_id / "metadata.json"
        if metadata.exists() and "first" in read_json(metadata).get("assets", {}):
            firsts += 1
    return {"project": project.name, "style": project.style.model_dump(), "episode": episode_id, "authoring": episode.authoring, "shots": len(episode.shots), "first_frames_recorded": firsts, "approved_characters": sum(c.state().approved for c in episode.characters), "jobs": [{"job_id": j.job_id, "shot": j.shot_id, "status": j.status, "prompt_id": j.prompt_id, "error": j.error} for j in jobs], "production_complete": False, "completion_rule": "Only qc PASS and complete verified assets establish delivery readiness"}
