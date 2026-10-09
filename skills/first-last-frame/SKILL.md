---
name: first-last-frame
description: 设计并生成单首帧或经参考编辑的首尾帧，保持人物与场景身份，支持单独重做尾帧及人工连续性验收。
---

# 首尾帧导演

## 触发场景

设计并生成单首帧或经参考编辑的首尾帧，保持人物与场景身份，支持单独重做尾帧及人工连续性验收。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 查看 frame_mode，静态或轻呼吸镜头使用单帧，不强制尾帧。
2. 首帧优先实际验证过的工作流；缺参考能力就明确标注身份未建立。
3. 用户审核首帧后，尾帧输入该首帧与目标动作；reference-editing 工作流必须有编辑模型和参考接线证据。
4. 普通Qwen/Z-Image文生图、VAE图生图不自动认定为语义参考编辑。缺能力时报告，交付单首帧预览和目标描述。
5. frames last --shots 单独生成/重试目标尾帧；检查手、道具、光线和姿势变化是否只有分镜要求部分。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：以SHOT007首帧为参考生成拿起卷轴的尾帧，身份和场景不变

```powershell
.\scripts\ai-drama.ps1 frames last --shots SHOT007 --family qwen-image-edit
```
