from pathlib import Path
from ai_drama.core.storage import read_json, write_json, write_text
from ai_drama.schemas.models import FrameAsset, QCIssue, QCReport
from ai_drama.pipeline.production import load_project, load_episode, episode_path, prompt_for
from ai_drama.frame_generator.jobs import verify_asset


def continuity(episode):
    issues = []
    previous = None
    for shot in episode.shots:
        if previous and previous.scene_id == shot.scene_id:
            if previous.axis_side != shot.axis_side and "越轴" not in shot.previous_link:
                issues.append(QCIssue(severity="ERROR", category="axis", shot_id=shot.shot_id, message="同场景发生未经说明的越轴"))
            for key, value in previous.continuity_out.items():
                if key in shot.continuity_in and shot.continuity_in[key] != value:
                    issues.append(QCIssue(severity="ERROR", category="state", shot_id=shot.shot_id, message=f"{key}: {value} → {shot.continuity_in[key]}，缺少动作交代"))
            if not shot.previous_link:
                issues.append(QCIssue(severity="WARNING", category="link", shot_id=shot.shot_id, message="未说明与上镜的衔接"))
        if shot.frame_mode == "dual" and shot.first_frame == shot.last_frame:
            issues.append(QCIssue(severity="WARNING", category="frames", shot_id=shot.shot_id, message="首尾状态相同，可使用单帧"))
        previous = shot
    return issues


def qc(root, episode_id="EP01", write=True):
    project, episode = load_project(root), load_episode(root, episode_id)
    issues = continuity(episode)
    if not project.style.confirmed:
        issues.append(QCIssue(severity="ERROR", category="style", message="视觉风格未确认锁定"))
    if episode.authoring == "extractive_draft":
        issues.append(QCIssue(severity="ERROR", category="script", message="抽取草稿未经过 Codex 语义改编与导演审阅"))
    for character in episode.characters:
        if not character.state().approved:
            issues.append(QCIssue(severity="ERROR", category="character", message=f"{character.name} 定妆未获用户确认"))
        if any("待" in getattr(character, field) for field in ["appearance", "face_shape", "facial_features", "hairstyle"]):
            issues.append(QCIssue(severity="ERROR", category="bible", message=f"{character.name} 设定未完成"))
        for path in character.state().reference_images:
            if not Path(path).is_file():
                issues.append(QCIssue(severity="ERROR", category="reference", message=f"角色参考图缺失：{path}", method="file"))
    for location in episode.locations:
        if "待" in location.layout or "待" in location.architecture:
            issues.append(QCIssue(severity="ERROR", category="location", message=f"{location.name} 结构未设计"))
    for shot in episode.shots:
        directory = episode_path(root, episode_id)/"shots"/shot.shot_id
        if not (directory/"first_prompt.json").is_file():
            issues.append(QCIssue(severity="ERROR", category="prompt", message="图片提示词缺失", shot_id=shot.shot_id, method="file"))
        metadata = read_json(directory/"metadata.json") if (directory/"metadata.json").exists() else {}
        if metadata.get("preview") or any(metadata.get("previews", {}).values()):
            issues.append(QCIssue(severity="ERROR", category="preview", message="身份未建立的预览，不能作为正式生产验收", shot_id=shot.shot_id))
        for frame in ["first"] + (["last"] if shot.frame_mode == "dual" else []):
            raw = metadata.get("assets", {}).get(frame)
            if not raw:
                issues.append(QCIssue(severity="ERROR", category="asset", message=f"{frame} 图片尚未成功生成", shot_id=shot.shot_id, method="file"))
                continue
            try:
                asset = FrameAsset.model_validate(raw)
                verify_asset(asset)
                expected = prompt_for(project, episode, shot).source_hash
                if metadata.get("source_hashes", {}).get(frame) != expected:
                    issues.append(QCIssue(severity="ERROR", category="provenance", message="图片与当前剧本/风格/角色版本不匹配，或缺少来源记录", shot_id=shot.shot_id))
                if asset.shot_id != shot.shot_id or asset.frame != frame:
                    raise ValueError("Asset assigned to wrong shot/frame")
                if abs(asset.width/asset.height - float(project.aspect_ratio.split(':')[0])/float(project.aspect_ratio.split(':')[1])) > 0.03:
                    issues.append(QCIssue(severity="ERROR", category="resolution", message=f"{frame} 画幅不符合项目设定", shot_id=shot.shot_id, method="file"))
                if asset.visual_review != "PASS":
                    issues.append(QCIssue(severity="ERROR" if asset.visual_review == "ERROR" else "WARNING", category="visual", message=f"{frame} 面部、手部、服装、道具与场景需要视觉复核：{asset.visual_review}；{asset.review_note}", shot_id=shot.shot_id, method="visual-model" if asset.review_method == "visual-model" else "human"))
            except (OSError, ValueError) as exc:
                issues.append(QCIssue(severity="ERROR", category="asset", message=str(exc), shot_id=shot.shot_id, method="file"))
        if not (directory/"video_prompt.txt").is_file():
            issues.append(QCIssue(severity="ERROR", category="doubao", message="视频提示词未导出", shot_id=shot.shot_id, method="file"))
    severity = "ERROR" if any(i.severity == "ERROR" for i in issues) else "WARNING" if issues else "PASS"
    report = QCReport(episode_id=episode_id, status=severity, issues=issues)
    if write:
        directory = episode_path(root, episode_id)/"qc"
        write_json(directory/"report.json", report)
        write_text(directory/"report.md", f"# 生产质检 · {severity}\n\n不提供虚构视觉评分。元数据检查不等于人物一致性视觉验收。\n\n" + "\n".join(f"- [{i.severity}] {i.shot_id or ''} {i.category} ({i.method})：{i.message}" for i in issues))
    return report
