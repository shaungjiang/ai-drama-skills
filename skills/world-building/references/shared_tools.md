# 共享工具层

定位用户的 ai-drama-skills 项目，不假定跨机器的绝对路径。先读取该项目 README.md、AGENTS.md、docs/cli.md、docs/architecture.md。项目级副本只负责发现，源技能位于 skills/，通过 scripts/install_skills.py 同步。

在项目根目录运行 scripts/ai-drama.ps1；其他生产项目使用全局参数 --project <path>，共享工作流库通过 --library <path>。全部全局参数放在子命令之前。使用 --help 查真实参数，读取 templates/*.schema.json 编写数据。

脚本负责状态持久化和检查，Codex负责语义创作与视觉判断；不调用付费LLM或视频API。--snapshot 是离线验证，不是运行验证。
