---
name: world-building
description: 建立修仙、都市或校园世界观、稳定场景和道具数据库，设计可跨镜头复用的空间、光源及状态规则。
---

# 世界场景道具导演

## 触发场景

建立修仙、都市或校园世界观、稳定场景和道具数据库，设计可跨镜头复用的空间、光源及状态规则。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 从剧本辨别明确设定与美术补充，不补造原著未给出的宗门关系或力量规则。
2. Location 记录平面结构、出入口、家具方位、光源和视觉锚点；Scene 记录时间天气。
3. 重要 Prop 分配独立 ID，记录持有人、外观、规则与物理状态。
4. 将地理方向转换为稳定摄影轴线，镜头 action 明确道具拿起、放下、转交。
5. 保存到 Episode 后用 locations generate 生成空间候选，并保留布局复核。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：设计石室，铜棺在桌右侧，窗口和出口在后续镜头保持不变

```powershell
.\scripts\ai-drama.ps1 locations generate --id LOC001
```
