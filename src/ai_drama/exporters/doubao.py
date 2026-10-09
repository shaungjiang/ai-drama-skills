from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from ai_drama.core.storage import write_text, write_json
from ai_drama.pipeline.production import load_episode, episode_path


def shot_prompts(shot, episode, mode):
    chars = {c.character_id: c.name for c in episode.characters}
    subject = "、".join(chars[c] for c in shot.characters) or "环境空镜"
    fields = [
        ("镜头编号", shot.shot_id), ("镜头时长", f"{shot.duration:g}秒"), ("主体", subject),
        ("首帧状态", shot.first_frame), ("人物动作", shot.action), ("表情变化", shot.expression),
        ("服装和头发运动", "随动作轻微运动，服装剪裁与饰品固定"), ("环境运动", shot.environment),
        ("镜头运动", shot.camera_movement), ("光影变化", "光源位置与方向固定，保持原有明暗关系"),
        ("动作节奏", "动作开始—变化—稳定，避免同时堆叠复杂动作"), ("尾帧状态", shot.last_frame),
        ("一致性约束", "保持输入图片人物脸型、发型、服装、场景结构、光源方向与道具；只允许指定动作变化"),
        ("负面约束", "不新增人物，不出现额外肢体，不换脸、不换衣，道具不凭空消失，无文字水印"),
    ]
    h3 = "\n\n".join(f"【{label}】\n{value}" for label, value in fields)
    natural = f"建议时长{shot.duration:g}秒。以首帧图片中的{subject}为准，起始状态：{shot.first_frame}。{shot.action}。表情：{shot.expression}。{shot.camera_movement}，{shot.size}，{shot.composition}。环境：{shot.environment}。结束状态：{shot.last_frame}。保持人物身份、服装、场景结构、道具和光线方向。动作克制且连续，发丝与衣料随动作轻微变化，不增加人物和肢体，不出现字幕、水印。"
    if mode == "dual" and shot.frame_mode == "dual":
        natural += "仅在你当前选择的豆包模式已确认支持首尾双帧输入时，上传首帧和尾帧并按两者过渡。"
    else:
        natural += "采用单首帧输入，尾帧状态是动作目标描述。"
    return h3, natural


def export(root, episode_id="EP01", mode="single", dual_confirmed=False, package=False, draft=False):
    if mode == "dual" and not dual_confirmed:
        raise ValueError("Confirm the selected Doubao mode supports dual-frame input before using --mode dual")
    episode = load_episode(root, episode_id)
    directory = episode_path(root, episode_id)
    text, checklist = [f"# {episode.title} · 豆包逐镜头提示词", "时长为创作建议，请在你选择的模式中核对可用时长；本工具不调用视频 API。"], ["# 镜头素材核对表", "未生成的图片不会创建占位文件。"]
    for shot in episode.shots:
        h3, natural = shot_prompts(shot, episode, mode)
        shot_dir = directory/"shots"/shot.shot_id
        write_text(shot_dir/"video_prompt.txt", h3 + "\n\n【豆包可复制提示词】\n" + natural)
        text += [f"\n## {shot.shot_id}", h3, "\n### 可复制提示词\n" + natural]
        first = (shot_dir/"first_frame.png").exists()
        last = (shot_dir/"last_frame.png").exists()
        checklist.append(f"- {shot.shot_id} · {shot.duration:g}秒 · 首帧{'存在' if first else '未生成'} · 尾帧{'存在' if last else '未生成' if shot.frame_mode == 'dual' else '不要求'} · 视觉检查待核对")
    write_text(directory/"doubao"/"video_prompts.md", "\n\n".join(text))
    write_text(directory/"doubao"/"shot_checklist.md", "\n".join(checklist))
    from ai_drama.validators.production import qc
    report = qc(root, episode_id)
    if package:
        if report.status != "PASS" and not draft:
            raise ValueError("Production package requires qc PASS. --draft exports explicitly incomplete review materials")
        destination = Path(root)/"output"/(episode_id + ("_DRAFT" if draft else "_production") + ".zip")
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            for file in directory.rglob("*"):
                if file.is_file() and "revisions" not in file.parts:
                    archive.write(file, file.relative_to(directory.parent))
        return {"prompts": str(directory/"doubao"/"video_prompts.md"), "package": str(destination), "qc": report.status}
    return {"prompts": str(directory/"doubao"/"video_prompts.md"), "qc": report.status}
