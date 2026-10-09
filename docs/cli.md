# CLI 使用与命令表

PowerShell 推荐 `.\scripts\ai-drama.ps1`；下文 `ai-drama` 指同一执行逻辑。全局参数必须放在子命令前：

```powershell
ai-drama --project '.\output\demo_projects\cultivation' --url 'http://127.0.0.1:8188' status
```

`--project` 是制作项目，`--library` 是可跨项目复用的配置/工作流库。两者默认本源码仓库。`--snapshot` 读取环境快照，只做静态/环境校验，不允许出图或激活。请使用 `--help` 查询每个子命令。

| 命令 | 实际行为 |
|---|---|
| init --source 文件 --name 名称 --duration 60 --style ... --confirm-style | 保留原文副本、源哈希与制作要求；已有项目拒绝重初始化 |
| analyze --names 林无道 江轻雪 | 提取原文事件块、显式人名与关系证据，标记需语义审阅 |
| script --names ... | 原文抽取草稿与Markdown，保留原文块，不声称专业改编 |
| script --import episode.json --reviewed | Pydantic验证 Codex 审阅稿、时长和引用关系，保存修订 |
| characters list / import --file 文件 | 列出或导入角色圣经与版本 |
| characters generate --id CHAR001 --view front/full/side/expression | 实际出图，结果始终是候选，独立角度不保证身份一致 |
| characters approve --id ... --reference 文件 --note 依据 | 保存原图副本与明确人工审批记录，不得伪造 |
| locations list / generate --id LOC001 | 场景库和实际空间候选图 |
| storyboard --episode EP01 --family z-image | 输出逐镜分镜和静态首尾状态提示词 |
| storyboard --prompts 文件 | 导入审阅后的 ImagePrompt 列表，支持中文或完整英文 |
| style detect | 基于题材推荐，不锁定 |
| style set 风格 --confirm | 用户明确确认后锁定，一集不会随机混合风格 |
| comfyui check --save 文件 | 实际检测节点、模型选项、版本、GPU、RAM和能力配方 |
| comfyui check --model-dir 授权目录 | 限定目录查模型文件及大小，不扫描整盘 |
| workflow inspect --directory 目录 | 只读盘点原图；转换不支持不代表原图已失效 |
| workflow plan --request 自然语言 | 按能力规划并报告缺失项 |
| workflow match --family ... --task ... | 查 ACTIVE 兼容工作流，不无条件重建 |
| workflow create --family ... --task ... | 生成可视化/API/元数据/说明，静态与环境检查后注册 |
| workflow import --file ... --task ... --evidence ... --bindings ... | 导入已安装图，复杂子图用前端API导出，高级能力需证据 |
| workflow validate --id ... | 图结构、类型、模型选项与环境复核；无运行成功则不激活 |
| workflow test --id ... --reference ... | 真实提交、等待、PNG解码保存，记录运行证据 |
| workflow repair --id ... --patch ... | 精确文件名修复、默认值或明确节点/接线patch，派生新版本 |
| workflow optimize --id ... | batch1、576×1024、兼容的CPU文本编码；派生版本，待真实测试 |
| workflow activate / disable --id ... | 激活需真实运行证据、实际图片和兼容校验；禁用后不自动匹配 |
| workflow list | 状态、版本、运行证据和环境指纹 |
| frames first --shots ... --preview | 真实首帧生成；预览明确不等于角色一致性验收 |
| frames last --shots ... --family qwen-image-edit | 编辑首帧生成尾帧，仅处理dual镜头，缺编辑能力则阻止 |
| frames first/last --regenerate | 独立重新生成，保留已有图历史副本 |
| frames validate | 输出图片完整性、尺寸和连续性QC |
| frames review --shot ... --frame first --result PASS/WARNING/ERROR --note ... | 记录实际视觉检查，不能用它伪造审批 |
| doubao export --mode single | H3+自然语言提示词与检查表，无视频API |
| doubao export --mode dual --dual-confirmed | 仅在所选豆包模式支持双帧已确认时使用 |
| doubao export --package [--draft] | 正式ZIP需qc PASS，草稿ZIP明确标记不完整 |
| status | 实际状态、出图数量与未完成任务 |
| qc | 逐项质检，区分文件、元数据与视觉检查 |
| jobs list / resume --job 文件 | 恢复原prompt_id，不重复提交运行中任务 |
| demo [--kind campus] [--destination 目录] | 完整离线草稿闭环；图片用实际生成命令完成 |

## 高级工作流导入

可视化图与API图不同；简单核心节点可转换，子图/绕过节点/自定义widget复杂图需在ComfyUI前端导出API格式。本工具不会为了转换而修改原始图。

例：已安装Qwen-Image-Edit（这里不安装），其能力证据JSON：

```json
{
  "task_type": "reference-editing",
  "source": "模型官方编辑说明及本机已验证工作流来源",
  "model_files": ["qwen_image_edit_fp8_e4m3fn.safetensors"],
  "reference_nodes": ["11"]
}
```

模型必须被图实际加载，参考节点必须真实存在且为LoadImage；普通Qwen/Z-Image文生图不接受声明为身份编辑。用户声明只是能力来源，之后仍需实际运行和视觉验收。

bindings 是参数到实际节点字段的映射，例如：

```json
{
  "positive": [["5", "prompt"]],
  "negative": [["6", "prompt"]],
  "seed": [["8", "seed"]],
  "steps": [["8", "steps"]],
  "width": [["7", "width"]],
  "height": [["7", "height"]],
  "reference": [["11", "image"]],
  "output_prefix": [["10", "filename_prefix"]]
}
```

有多个LoadImage时必须明确语义，不能把同一图片填进不同人物/场景输入。多角色首帧可配置 `reference_CHAR001`、`reference_CHAR002`；单角色用 `reference`。导入参考条件首帧工作流的task设为text-to-image，实际能力通过来源证据、模型和图接线复核。

## 修复与恢复

接线/节点别名不猜测：先查object_info，再提供补丁列表：

```json
[{"node": "8", "inputs": {"model": ["4", 0]}}]
```

修复/优化版本不会继承运行验证，需重新test/activate。OOM只在服务器明确报错后重试，最多三次，逐次减分辨率并记录；新画幅可能不满足正式QC。无法确定提交是否成功时标记UNKNOWN，先查服务器队列/历史再关联prompt_id，不盲目重复提交。

任务JSON及request/resource日志保存在共享库output/jobs。`jobs resume --job` 保留原prompt_id；进程崩溃遗留生产锁时，先核对锁内PID确实退出，再手工移除锁。全局串行锁只协调使用同一library的本工具实例，外部工具不受此锁管理。

修改角色、剧本或风格后先更新storyboard，旧图片来源哈希会被QC拦截。参考图审批不会自动证明每镜身份已合格。
