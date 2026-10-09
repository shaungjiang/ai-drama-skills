# AI Drama Studio 2.0

以 Codex 负责创作与视觉判断、Python 负责可追溯执行、ComfyUI 负责图片生成的 AI 漫剧工具链。包含 **13 个 Skills、真实 CLI、Pydantic 数据模型、双风格配置、工作流构建/验证/复用、串行出图、首尾帧能力检查、豆包提示词及素材包导出**。

视频由用户在豆包手动生成。本项目不调用豆包视频 API，不自动配音、剪辑或合成视频，也不下载模型。

## 当前交付范围

- 从原文建立项目、人物关系证据、角色/场景/道具库；Codex 编写审阅后的 Episode JSON 并导入。
- `script` 不带导入文件时生成可追溯的**抽取草稿**，不是语义小说改编器。专业改编由 Skills 引导 Codex 完成，不需要额外 LLM API。
- 修仙3D国漫与现代影视写实独立配置。自动推荐等待确认；用户明确选定后锁定。
- 基于实际 `/object_info` 验证 Qwen-Image / Z-Image 配方，生成**不同格式**的可视化和 API JSON。
- 原工作流只读；修改、修复和优化产生新版本。批量用 ACTIVE 工作流，首个单任务运行验证后复用。
- 角色定妆候选必须人工批准。普通文生图缺少身份参考输入时仅能生成标记为预览的镜头。
- 尾帧需要真实编辑模型和参考接线。未安装编辑模型时如实阻止，不用两次文生图冒充一致性。
- 控制姿势/局部重绘/量化变体通过带能力证据的已安装 API 工作流导入；当前没有覆盖全部第三方图的自动配方。
- 元数据与文件检查自动化；面部、手部、服装、空间与审美仍需视觉验收，不输出虚构质量评分。

本机实测及限制见 [验收报告](docs/acceptance.md)。正式素材包需要 `qc PASS`；不完整包名称含 `DRAFT`。

## Windows 安装

需要 Python 3.11 或以上。不要使用 ComfyUI 的 Python 安装本项目依赖。

```powershell
Set-Location 'D:\你的目录\ai-drama-skills'
.\scripts\install.ps1 -Python 'C:\你的独立Python\python.exe'
.\scripts\ai-drama.ps1 --help
.\scripts\run_tests.ps1
```

已有独立虚拟环境时也可 `python -m pip install -e '.[test]'`，然后使用 `ai-drama`。本仓库以源码/可编辑安装方式运行，配置和 Skills 与源码一起保存。

## 一条命令运行演示

```powershell
.\scripts\ai-drama.ps1 demo
.\scripts\ai-drama.ps1 demo --kind campus
```

第一条创建《无敌收尸系统》60秒、9:16、10镜头的**制作演示草稿**，第二条创建独立12秒校园写实测试。命令会导出剧本、角色设定、分镜、图片提示词、H3与自然语言提示词及草稿ZIP，**不会假装已经生成图片**。再次运行复用已有演示项目。

## 使用 Skills 与自然语言

```powershell
.\.venv\Scripts\python.exe scripts\install_skills.py
```

复制到项目 `.agents/skills`；同名内容不同会拒绝覆盖。以项目为工作目录打开新 Codex 聊天，调用 `$ai-drama-director`：

> 把 input/novel.txt 制作成60秒9:16的3D国漫，保留原著核心设定，先给角色定妆候选，使用已有 ComfyUI 输出镜头图片与豆包提示词。

源 Skills 位于 `skills/`；共享代码位于 `src/ai_drama/`。用户级安装可显式指定 `--target`，先检查当前 Codex 的目录规则与同名冲突。文件扫描验证不等于当前聊天已热加载，需新聊天核对技能入口。

官方资料：[Skills 构建](https://developers.openai.com/plugins/build/skills)、[Codex 项目级 Skills 示例](https://developers.openai.com/blog/skills-agents-sdk)。用户指定的 [openai/skills](https://github.com/openai/skills) 仓库已提示迁移到新的插件资料。

## 连接 ComfyUI 与生产示例

启动你现有的 ComfyUI。默认 `http://127.0.0.1:8188`，可以编辑 `config/comfyui.yaml`，或使用 `--url` / `COMFYUI_URL`。

```powershell
.\scripts\ai-drama.ps1 comfyui check --save .\output\environment.json
.\scripts\ai-drama.ps1 workflow inspect --directory 'D:\你授权的工作流目录'
.\scripts\ai-drama.ps1 workflow plan --request '搭建适合8GB的Z-Image角色定妆工作流'
.\scripts\ai-drama.ps1 workflow create --family z-image
# 使用上一步返回的 workflow_id
.\scripts\ai-drama.ps1 workflow test --id '<workflow_id>'
.\scripts\ai-drama.ps1 workflow activate --id '<workflow_id>'
.\scripts\ai-drama.ps1 workflow match --family z-image --task first-frame
```

```powershell
# 全局 --project / --library / --url 放在子命令之前
.\scripts\ai-drama.ps1 --project .\output\demo_projects\cultivation characters generate --id CHAR001 --view front
# 只有用户确实确认该图片后执行审批
.\scripts\ai-drama.ps1 --project .\output\demo_projects\cultivation characters approve --id CHAR001 --reference '<图片路径>' --note '用户确认记录'
# 普通文生图身份未建立，仅做预览；生产需导入有身份参考能力的工作流
.\scripts\ai-drama.ps1 --project .\output\demo_projects\cultivation frames first --shots SHOT001 --preview
.\scripts\ai-drama.ps1 --project .\output\demo_projects\cultivation doubao export --package --draft
```

缺少编辑模型时 `frames last` 返回明确缺失能力，而不下载模型。完整示例、导入证据格式、恢复与所有命令见 [CLI 文档](docs/cli.md) 和 [架构说明](docs/architecture.md)。

## 环境与隐私

不升级 ComfyUI/PyTorch/CUDA，不修改环境变量持久设置，不覆盖原始工作流。API 出图会在 ComfyUI 自身输出目录保存结果，再下载复制到项目；授权的参考图会按内容哈希上传到 ComfyUI input。大模型和自定义节点安装需要另行决定。

`.gitignore` 排除生成素材、小说输入、虚拟环境、机器检测报告、注册表和模型。公开仓库只包含代码、通用配置、合成示例、脱敏测试夹具和汇总报告。部署到远程 ComfyUI 前自行确认素材传输目的地。
