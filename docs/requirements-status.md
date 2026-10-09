# 需求与验证对应

| 原需求 | 实现位置 / 验证 | 边界 |
|---|---|---|
| 13 Skills / 1–4 | skills、scripts/install_skills.py、test_skills_cli.py | 文件规范与发现目录已验；当前会话热加载不作保证 |
| 剧本与分镜 / 5–10 | pipeline、schema、style_router、双演示项目、test_production.py | 自动抽取是草稿；Codex负责语义审阅导入 |
| 环境、节点、模型 / 11–18 | client、graph、adapters、workflow inspect/plan/create/import | 特定配方实机校验；第三方复杂图用API导出 |
| API出图与保存 / 19–20 | client、jobs、实机报告 | 与模拟传输测试分开 |
| 工作流复用 / 21–30 | registry、bindings、10镜头实测、test_workflows.py | 原图和版本不覆盖；修复不猜模型或节点别名 |
| 首帧 / 31 | frames first、character generate、locations generate | 文生图预览不等于身份一致 |
| 尾帧 / 32–35 | reference-editing配方、frames last、jobs resume、continuity | 本机缺编辑模型，真实尾帧未验证 |
| 豆包 / 36–39 | exporters/doubao.py、两份文案、ZIP | 手动选择豆包模式，无视频API |
| 低显存 / 40–44 | batch1、exclusive锁、OOM恢复、资源日志 | 采样范围实测；不承诺外部程序资源控制 |
| 交付 / 45–50 | README、CLI、测试、示例、acceptance.md | 未验能力明确列出，正式包有QC门槛 |

`workflows/` 中通用范例不是跨电脑可直接ACTIVE的注册项；每台设备先环境检查、运行test，再激活。当前工作区的实际注册项与私有图片仅保留本地，不公开上传。
