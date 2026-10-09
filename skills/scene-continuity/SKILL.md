---
name: scene-continuity
description: 检查漫剧镜头的轴线、人物状态、服装版本、手部道具与空间衔接，区分元数据检查和实际视觉复核。
---

# 连续性检查

## 触发场景

检查漫剧镜头的轴线、人物状态、服装版本、手部道具与空间衔接，区分元数据检查和实际视觉复核。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 先比对连续镜头 scene_id、axis_side、state_versions 和 continuity_in/out。
2. 越轴需在 previous_link 明确交代；左右手、道具位置与持有者变化需有动作。
3. 检查已生成首尾帧真实文件，使用 frames validate 获取元数据和文件检查。
4. 逐图视觉复核脸型、发型、饰品、服装、道具、灯光和场景结构；记录 PASS/WARNING/ERROR 与观察依据。
5. 用 frames review 保存人类验收；不要将提示词相同、Seed相同或哈希不同当身份一致证据。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：检查林无道拿起藏尸图前后，手和卷轴是否连续

```powershell
.\scripts\ai-drama.ps1 frames validate --episode EP01
```
