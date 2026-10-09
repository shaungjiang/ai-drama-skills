---
name: novel-to-script
description: 把小说改编为30至120秒等指定时长漫剧，提取人物关系、冲突和设定，产出可导入 AI Drama Studio 的结构化剧本与分镜草案。
---

# 小说改编导演

## 触发场景

把小说改编为30至120秒等指定时长漫剧，提取人物关系、冲突和设定，产出可导入 AI Drama Studio 的结构化剧本与分镜草案。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 完整读原文，记录关键事实、人物关系与情节因果，引用证据不凭空补设定。
2. 按目标时长压缩支线，保留主要冲突、开场钩子和结尾悬念，将心理活动变为可见行动。
3. Codex 完成语义改编，编写符合 Episode schema 的 JSON；根据情绪设计动作和对白。
4. 确保所有 scene/character/location/prop ID 对得上，镜头总时长等于剧集时长，每镜建议不超过15秒。
5. script --import <episode.json> --reviewed 进行 Pydantic 校验并输出 Markdown。不提供完整原著时只改编已提供设定。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：将这篇小说改成60秒剧本，保留诅咒、铜棺和十倍强化的关键设定

```powershell
.\scripts\ai-drama.ps1 --project .\my-drama script --import .\episode.json --reviewed
```
