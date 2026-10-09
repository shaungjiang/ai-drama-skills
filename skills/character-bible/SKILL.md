---
name: character-bible
description: 建立并版本化漫剧角色的五官、发型、服装、饰品、武器和身份锚点；生成候选定妆图并管理用户审批。
---

# 角色圣经管理

## 触发场景

建立并版本化漫剧角色的五官、发型、服装、饰品、武器和身份锚点；生成候选定妆图并管理用户审批。

## 输入要求

用户制作目标、项目路径、原文或Episode JSON，以及对应的已有角色图/场景/工作流。具体读取 [共享工具说明](references/shared_tools.md)。

## 工作步骤

1. 使用 Character/CharacterState 模型建立全部外貌字段和稳定角色 ID。原图优先，禁止擅自修改。
2. 每次换装建立递增 state version；镜头明确引用 state_versions，避免旧服装串入新镜头。
3. characters generate 生成 front/full/side/expression 候选；独立文生图的不同角度不自动视为同一身份。
4. 让用户确认候选文件后 characters approve --reference --note 锁定。不得自行填写虚假审批记录。
5. 批量镜头必须复用已批准身份；没有参考条件能力则只能预览并报告一致性未建立。

## 输出格式

共享 CLI 产生的JSON、Markdown与真实PNG及状态；报告实际路径、审批状态、测试范围和缺失能力。创作数据遵守项目 `templates/episode.schema.json` 与 `templates/image_prompt.schema.json`。

## 使用的工具

优先已安装的 `ai-drama` 或项目 `scripts/ai-drama.ps1`；执行逻辑统一使用 `src/ai_drama`。需要视觉确认时读取实际图片。

## 错误处理

缺输入先读取已有项目；真正影响结果的缺项再询问。环境离线可处理剧本与导出，不能声称真实出图。模型节点缺失报告能力，不擅自下载、安装、升级。未审批角色停在候选状态。任务超时按记录恢复，原素材与原工作流另存保留。

## 使用示例

用户：为林无道建立稳定角色圣经，先给定妆候选图供我确认

```powershell
.\scripts\ai-drama.ps1 characters generate --id CHAR001 --view front
```
