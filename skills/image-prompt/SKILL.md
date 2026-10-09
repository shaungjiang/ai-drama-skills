---
name: image-prompt
description: 根据角色、场景、风格和分镜编写可注入实际ComfyUI模型的中英文静态图片提示词与约束。
---

# 图片提示词导演

## 触发场景

根据角色、场景、风格和分镜编写可注入实际ComfyUI模型的中英文静态图片提示词与约束。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 读取角色批准状态、服装版本、场景光源、镜头景别和已验证模型能力。
2. 按风格→身份→外貌→服装→静态姿态→表情→场景→光影→景别→构图→约束组织提示词。
3. 图片只描述一个瞬间；把视频动作过程拆成首尾状态，禁止把动态视频文案直接复制进图片输入。
4. Z-Image Turbo CFG=1 的 negative 可能不生效，关键约束写进正向描述；Qwen 依实际工作流注入。
5. 自动输出中文；英文由 Codex 编写 ImagePrompt JSON 后 storyboard --prompts 导入，保证不是伪翻译。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：为SHOT007写中文和英文首帧提示词，右手与卷轴完整入画

```powershell
.\scripts\ai-drama.ps1 storyboard --prompts .\reviewed_prompts.json
```
