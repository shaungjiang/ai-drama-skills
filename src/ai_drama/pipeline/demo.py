from __future__ import annotations

import shutil
from pathlib import Path
from ai_drama.schemas.models import Character, CharacterState, Location, Scene, Prop, Shot, Episode
from ai_drama.pipeline.production import initialize, save_episode, storyboard
from ai_drama.core.storage import write_json
from ai_drama.exporters.doubao import export


def cultivation():
    lin = Character(character_id="CHAR001", name="林无道", gender="男", age="约25岁", identity="穿越修仙世界的青年", appearance="青年东亚男性，清瘦而坚毅，黑发束起，墨青古装", face_shape="清晰椭圆脸，下颌自然", facial_features="平直剑眉，深棕眼睛，直鼻，薄唇", hairstyle="黑色长发高束，额前两缕碎发", hair_color="黑色", skin_color="自然浅米肤色", physique="修长，正常头身比例", personality="由惊惧转为冷静求生", visual_anchors=["墨青交领", "右侧发束", "古铜方扣腰带"], states=[CharacterState(state_id="STATE_LIN_01", clothing="墨青交领长袍，暗银窄边，古铜方扣黑腰带", health="受诅咒，仅剩十个时辰")])
    jiang = Character(character_id="CHAR002", name="江轻雪", gender="女", age="约23岁", identity="林无道未婚妻；通过诅咒印记与回忆表现", appearance="成年东亚女性，冷静疏离，素白古装", face_shape="自然鹅蛋脸", facial_features="细长眉，深棕杏眼，挺鼻，唇形克制", hairstyle="黑色长发半挽，单枚银簪", hair_color="黑色", skin_color="自然浅肤色", physique="修长自然", personality="疏离，动机未由素材交代", visual_anchors=["单枚银簪", "素白交领", "冷色眼神"], states=[CharacterState(state_id="STATE_JIANG_01", clothing="素白交领长裙，银灰窄边", accessories=["单枚银簪"])])
    location = Location(location_id="LOC001", name="山中石室", layout="南侧石桌，东侧床榻，西侧窄窗；铜棺出现于石桌右侧地面，入口在北侧后景；摄影机始终在桌子南侧", architecture="青灰石墙，旧木桌，石板地面，东方修仙洞府", visual_anchors=["西侧暖色油灯", "北侧拱形入口", "石桌右侧留空地面"])
    scene = Scene(scene_id="SCENE001", location_id=location.location_id, characters=["CHAR001"], time="深夜", weather="窗外无雨，微风", lighting="左侧油灯暖主光，西窗冷月光；系统出现时局部古铜微光", objective="在寿命倒计时前发现求生路径")
    props = [Prop(prop_id="PROP001", name="葬天铜棺", appearance="旧青铜长棺，暗金浮雕，棺盖闭合，长度与成人躯体相符", owner_id="CHAR001"), Prop(prop_id="PROP002", name="藏尸图", appearance="深褐古卷，古铜边扣，展开后呈现点状光标，无可读文字", owner_id="CHAR001", rule="记录方圆万里内强者尸体位置；初始强化倍数十倍")]
    beats = [
        ("极近特写", "略俯视", "固定机位", "林无道睁眼，急促呼吸后努力平稳下来", "惊惧", "林无道：我只剩十个时辰？", "林无道闭眼躺在东侧床榻，眉头紧锁", "林无道睁眼，眼神聚焦", "仅剩十个时辰寿命", "dual", [], "视线引导到手腕"),
        ("手腕特写", "俯视", "固定机位", "林无道把右手腕转向油灯，查看诅咒印记", "怀疑与压抑", "林无道：江轻雪……为何咒我？", "右手腕自然放在胸前，暗红诅咒纹路隐约显现", "右手腕转向左侧灯光，印记清晰但无文字", "受到未婚妻江轻雪的诅咒", "dual", [], "右手运动匹配"),
        ("中近景", "平视", "固定机位", "林无道坐在床沿，注视空中逐渐汇聚的古铜光点", "由恐惧转为警觉", "系统：无敌收尸系统已觉醒。", "林无道已经坐在床沿，双脚落地，右手垂下", "林无道坐姿不变，视线转向前方光点", "觉醒无敌收尸系统", "single", [], "音桥引出系统"),
        ("全景", "平视", "缓慢平移少量距离，展示地面空间", "古铜光点在石桌右侧汇聚，形成闭合铜棺；林无道停在床沿观察", "戒备", "系统：获得葬天铜棺。", "石桌右侧地面空置，林无道坐于东侧床沿", "闭合青铜长棺位于石桌右侧地面，林无道位置固定", "获得葬天铜棺", "dual", ["PROP001"], "空间交代与视线匹配"),
        ("铜棺特写", "低机位", "固定机位", "铜棺暗金纹路短暂亮起，随后稳定", "庄严、神秘", "系统：收尸可获强化。", "青铜棺盖闭合，纹路微暗，地面接触影明确", "棺盖保持闭合，古铜纹路柔和发光", "葬天铜棺", "single", ["PROP001"], "材质细节接空间全景"),
        ("中景", "平视", "固定机位", "古卷在石桌中央显现，林无道起身走到桌前后停下", "专注", "系统：获得藏尸图。", "林无道站在石桌前，石桌中央汇聚微光，铜棺在右侧后景", "古卷平放桌中央，林无道双手在桌沿外，不遮挡古卷", "获得藏尸图", "dual", ["PROP001", "PROP002"], "起身与移动在动作描述交代"),
        ("手部近景", "略俯视", "固定机位", "林无道右手靠近古卷，捏住卷轴边扣并轻轻拿起", "谨慎", "林无道：藏尸图？", "古卷平放桌面，右手位于卷轴右侧一掌距离", "右手持卷轴边扣，古卷抬离桌面少许；左手仍在桌沿", "藏尸图", "dual", ["PROP002"], "右手、道具动作匹配"),
        ("过肩近景", "俯视", "固定机位", "林无道双手展开古卷，点状光标在图面亮起", "惊讶后思考", "系统：可查方圆万里内强者尸体位置。", "古卷已置回桌面，双手分别位于卷轴左右端，卷面半开", "古卷展开，点状光标显现，无文字，左右手各持卷轴一端", "藏尸图记录方圆万里内强者尸体的位置", "dual", ["PROP002"], "先放回桌面再展开，保持轴线"),
        ("面部近景", "平视", "轻微推近", "林无道从地图上抬起目光，眉头松开", "决意逐渐形成", "系统：初始强化倍数——十倍。", "林无道站在桌前低头看图，双肩平稳", "林无道抬头，目光坚定，仍站在桌前", "初始强化倍数为十倍", "dual", ["PROP002"], "眼神从地图移向出口"),
        ("中景", "平视", "固定机位", "林无道将古卷收拢，右手稳稳握住，目光看向北侧入口", "冷静、坚定", "林无道：那就从第一具尸体开始。", "古卷收拢于桌上，林无道右手按在边扣上", "林无道右手持古卷，站位不变，望向北侧入口；铜棺仍在原地", "林无道觉醒系统，获得铜棺和藏尸图，决定求生（原创表演补充）", "dual", ["PROP001", "PROP002"], "以出口视线形成悬念"),
    ]
    shots = []
    for i, (size, angle, movement, action, expression, dialogue, first, last, evidence, mode, prop_ids, link) in enumerate(beats):
        shots.append(Shot(shot_id=f"SHOT{i+1:03}", scene_id="SCENE001", characters=["CHAR001"] if i != 4 else [], duration=6, size=size, angle=angle, composition="竖屏三分构图，留出人物视线空间；手和关键道具完整入画", camera_movement=movement, action=action, expression=expression, dialogue=dialogue, first_frame=first, last_frame=last, frame_mode=mode, previous_link=link, next_link=beats[i+1][-1] if i+1<len(beats) else "结尾悬念", source_excerpt=evidence, state_versions={"CHAR001": 1} if i != 4 else {}, prop_ids=prop_ids, environment="油灯火焰轻微跳动，其他结构固定"))
    return Episode(title="无敌收尸系统 · 第1集", duration=60, characters=[lin, jiang], locations=[location], scenes=[scene], props=props, shots=shots, relationships=[{"from": "CHAR001", "to": "CHAR002", "relation": "未婚夫妻", "evidence": "用户提供故事设定：未婚妻江轻雪诅咒林无道"}], synopsis="受诅咒只剩十个时辰的林无道觉醒收尸系统，获得铜棺和藏尸图，决定寻找求生机会。", hook="只剩十个时辰", cliffhanger="地图中的第一具强者尸体在哪里？", authoring="authored_demo")


def campus():
    character = Character(character_id="CHAR001", name="陈默", gender="男", age="18岁大学新生", identity="现代大学生（独立虚构演示）", appearance="成年东亚青年，黑色短发，浅蓝衬衫", face_shape="自然椭圆脸", facial_features="平直眉，深棕眼睛，直鼻", hairstyle="黑色短发，整齐侧分", hair_color="黑色", skin_color="自然米肤色，保留皮肤纹理", physique="自然身形，正常比例", personality="略紧张而友善", visual_anchors=["浅蓝棉衬衫", "黑色帆布包", "侧分短发"], states=[CharacterState(state_id="STATE_CAMPUS_01", clothing="浅蓝棉衬衫，深灰长裤", accessories=["黑色帆布包"])])
    location = Location(location_id="LOC001", name="大学教室", layout="左侧三扇窗，右侧教室门，前方黑板，四列木质课桌，人物位于靠窗第二排；摄影机在桌列右侧", architecture="现代大学教室，自然透视，浅色墙面", visual_anchors=["三扇左窗", "右侧入口", "四列木桌"])
    scene = Scene(scene_id="SCENE001", location_id="LOC001", time="下午", weather="晴天", lighting="左窗柔和自然光，右侧墙面反光补光", characters=["CHAR001"], objective="入学第一天的紧张转为释然")
    shots = [Shot(shot_id="SHOT001", scene_id="SCENE001", characters=["CHAR001"], duration=6, size="中景", action="陈默放下帆布包，坐在靠窗第二排，抬眼看向教室门", expression="轻微紧张", first_frame="陈默坐于靠窗第二排，帆布包在右侧桌面", last_frame="陈默抬眼看向画面右侧的门，包仍在桌上", dialogue="陈默：新的开始。", previous_link="建立空间", next_link="视线匹配", state_versions={"CHAR001": 1}), Shot(shot_id="SHOT002", scene_id="SCENE001", characters=["CHAR001"], duration=6, size="近景", action="陈默肩膀放松，轻轻微笑", expression="释然", first_frame="陈默看向门口，肩膀略紧绷", last_frame="同一站位与服装，陈默自然微笑", previous_link="视线匹配，摄影机保持轴线A", state_versions={"CHAR001": 1})]
    return Episode(title="校园 · 独立影视写实测试", duration=12, characters=[character], locations=[location], scenes=[scene], shots=shots, synopsis="大学新生在教室中迎来新的开始。", hook="入学第一天", cliffhanger="", authoring="authored_demo")


def create_demo(library, kind, destination=None):
    directory = Path(destination) if destination else Path(library)/"output"/"demo_projects"/kind
    if (directory/"project.json").exists():
        return {"project": str(directory), "reused": True}
    episode = cultivation() if kind == "cultivation" else campus()
    style = "cinematic_3d_donghua" if kind == "cultivation" else "cinematic_live_action"
    shutil.copytree(Path(library)/"config", directory/"config", dirs_exist_ok=True)
    source = Path(library)/"examples"/(kind+"_source.txt")
    initialize(directory, source, episode.title, episode.duration, "9:16", style, True)
    save_episode(directory, episode)
    storyboard(directory)
    exported = export(directory, package=True, draft=True)
    return {"project": str(directory), "shots": len(episode.shots), "duration": episode.duration, "style": style, "images_generated": False, **exported}
