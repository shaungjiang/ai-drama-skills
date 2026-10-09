---
name: comfyui-image-generator
description: 使用已验证且兼容的ComfyUI工作流提交图片、注入参数、查询队列、保存PNG和生成元数据，并恢复失败任务。
---

# ComfyUI出图执行

## 触发场景

使用已验证且兼容的ComfyUI工作流提交图片、注入参数、查询队列、保存PNG和生成元数据，并恢复失败任务。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. comfyui check 读取实际节点、模型选择与运行环境，不安装/升级任何节点模型。
2. workflow match 优先 ACTIVE 且输入兼容的模板；不能因为镜头、提示词或Seed变化重建。
3. 按 binding 深拷贝注入提示词和分辨率，串行 batch 1。仅在队列空闲时切模型并释放旧模型。
4. 保存 job request、prompt_id、参数、资源日志和实际输出。timeout 保留运行状态并 jobs resume。
5. 仅历史执行成功、PNG完整读取且文件保存后标 SUCCEEDED。UNKNOWN 提交先人工查服务器历史，最多3次明确失败重试。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：用已验证Z-Image工作流生成镜头首帧，保存种子、参数和结果

```powershell
.\scripts\ai-drama.ps1 frames first --shots SHOT001 --preview
```
