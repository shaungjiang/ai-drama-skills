---
name: ai-drama-director
description: 从小说和制作要求组织 AI Drama Studio 项目，调度剧本、资产、分镜、ComfyUI 出图、首尾帧和豆包素材交付。适用于完整漫剧制作及断点续作。
---

# AI漫剧总导演

## 触发场景

从小说和制作要求组织 AI Drama Studio 项目，调度剧本、资产、分镜、ComfyUI 出图、首尾帧和豆包素材交付。适用于完整漫剧制作及断点续作。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 读取项目状态、原文和已有资产；初始化时记录源文件哈希、剧集时长与画幅。
2. 通过 novel-to-script 生成并导入审阅后的 Episode JSON。不要把 extractive_draft 当专业改编。
3. 按题材推荐风格；明确指定的风格可以锁定，自动推荐先获取用户确认。
4. 建立角色、场景、道具和分镜；角色候选必须由用户确认后执行 characters approve。
5. 先查工作流注册表，再环境验证。参数变化复用模板；缺少任务能力才创建。
6. 角色与场景候选、首帧和尾帧任务均持久化。API 超时恢复 prompt_id，不重复提交。
7. 缺少身份参考或编辑能力时，交付带明确状态的草稿；只有文件真实生成且 QC PASS 才报告素材包完成。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：把小说做成60秒9:16国漫，使用已有ComfyUI，输出豆包图片和提示词

```powershell
.\scripts\ai-drama.ps1 --project .\my-drama status
```
