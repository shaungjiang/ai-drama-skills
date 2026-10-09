---
name: storyboard-director
description: 为漫剧编写含景别、机位、构图、视线、轴线、动作、台词和首尾状态的专业结构化分镜，维护时长和衔接。
---

# 影视分镜导演

## 触发场景

为漫剧编写含景别、机位、构图、视线、轴线、动作、台词和首尾状态的专业结构化分镜，维护时长和衔接。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 每场戏标出人物目标、阻力、行动与结果变化；镜头服务叙事。
2. 用稳定 scene_id/shot_id 编写 Shot；明确 axis_side、eye_line 和 previous_link/next_link。
3. 控制景别节奏，固定机位用于对白和精细手部动作，轻推用于情绪转折；不要每镜环绕。
4. 复杂拿物、站起、移位分阶段设计，记录 continuity_in/out 和 state_versions。
5. 合理选择 single/dual，静态特写可单帧；导入 Episode 后 storyboard 生成逐镜图片提示词。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：设计一集60秒修仙分镜，右手拿卷轴，桌子和铜棺位置保持连续

```powershell
.\scripts\ai-drama.ps1 storyboard --episode EP01 --family z-image
```
