---
name: comfyui-workflow-builder
description: 读取ComfyUI实际节点与模型，用可验证配方按需构建可视化和API工作流，管理版本、修复、运行验证和复用。
---

# 智能工作流构建

## 触发场景

读取ComfyUI实际节点与模型，用可验证配方按需构建可视化和API工作流，管理版本、修复、运行验证和复用。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 先 object_info/system_stats 与明确授权目录检测；workflow inspect 只扫描指定目录。
2. workflow match 优先兼容 ACTIVE 模板；普通提示词、参考文件、角色和镜头变化通过参数注入。
3. workflow plan 分类任务，文生图使用经来源核实且 exact model tuple 可用的Qwen/Z-Image配方。量化变体需导入其已工作图，不能猜节点。
4. workflow create 根据实际端口定义生成两个不同格式JSON、metadata和README；控制、重绘需现成兼容配方/evidence。
5. 先静态、再环境、再实际 workflow test，只有真实PNG才能 runtime_verified，再 activate 用于批量。
6. repair/optimize 派生新版本，未知接线/节点名要求明确patch；原图不覆盖，关键功能不删除。OOM参数回退保留日志，最多3次重试。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：搭建Qwen-Image国漫工作流，先检查模型节点并复用已有模板

```powershell
.\scripts\ai-drama.ps1 workflow create --request "搭建一个适合8GB的Z-Image角色定妆工作流"
```
