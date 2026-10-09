---
name: visual-style-director
description: 推荐、确认并锁定3D国漫或影视写实风格，控制材质、造型、色彩、光源、空间层次与跨镜头统一。
---

# 视觉美术导演

## 触发场景

推荐、确认并锁定3D国漫或影视写实风格，控制材质、造型、色彩、光源、空间层次与跨镜头统一。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 读取两套独立 YAML 风格配置与项目现有状态。修仙/玄幻推荐 cinematic_3d_donghua；现实/校园推荐 cinematic_live_action。
2. 用户明确指定优先服从；AUTO 是建议，style set --confirm 必须有用户依据。
3. 以自然五官比例、固定服装身份锚点、可追踪光源、克制主辅色与前中后景层次做美术指导。
4. 用低数量静帧检查塑料皮肤、廉价建模、蜡像皮肤、材质混乱与视觉焦点。
5. 锁定后普通镜头变化不切换风格。切风格时先匹配已有兼容工作流，重新输出提示词并复核旧资产。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：修仙剧使用精致3D国漫，现代校园测试单独使用影视写实

```powershell
.\scripts\ai-drama.ps1 style set cinematic_3d_donghua --confirm
```
