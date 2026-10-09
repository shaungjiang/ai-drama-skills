# 架构与证据边界

## 共享执行层

13个Skills为Codex提供创作、调用和验收指南。语义小说改编、美术设计、分镜与视觉判断由Codex完成；CLI负责模式校验、持久化、接口调用与文件证据，不内置收费LLM或视频服务。

`schemas` 定义 Project、Episode、Scene、Shot、Character、CharacterState、Location、Prop、VisualStyle、ImagePrompt、FrameAsset、GenerationJob、WorkflowDefinition、WorkflowRegistryEntry、QCReport。稳定ID、来源哈希、角色状态版本、工作流ID、job_id、prompt_id和PNG哈希建立追溯链。JSON写入为原子替换；Episode变更保留修订。

`pipeline` 管理草稿/审阅稿、角色场景库与分镜；`style_router` 负责AUTO/MANUAL/LOCKED；`validators` 区分图检查、元数据连续性和真实文件检查；`exporters` 输出H3/自然语言文案与ZIP。

## 按需构建和复用

`comfyui.Client` 读取实际object_info/system_stats。环境指纹包含接口和版本信息，排除空闲显存、RAM占用和上传图片枚举。模型/节点变化需要兼容性复核，普通图片上传或占用变化不触发重建。

独立Qwen/Z-Image适配器提供经官方资料确认的精确模型组合与参数配方；图构建器按实时定义验证所用每个输入、选择、输出和连接。未支持的量化版本通过已有API图导入，不能凭名字映射到普通模型。

注册表在共享库根目录。状态链：CREATED → STATIC_VALIDATED → ENV_VALIDATED → RUNTIME_VERIFIED → ACTIVE；另有FAILED/DISABLED/OUTDATED。构建保存过程完成静态与环境校验后才注册，运行证据来自成功任务与实际PNG。原图外部编辑引起图哈希改变时标记OUTDATED；优化/修复创建新ID和parent_id，不继承运行成功。

生成先match。ACTIVE匹配后复制API图并按bindings注入；同一类型任务没有匹配时复用未运行的结构候选，对一个任务真实测试后激活。仍无图才按需构建。镜头编号、名字、台词、种子、普通分辨率或提示词变化不创建模板。

`workflow.json` 是含nodes/links/widget布局的可视化格式；`workflow_api.json` 是节点ID到class_type/inputs的执行图。导入自定义UI/子图时，不猜widgets_values顺序，要求前端API导出。类型及范围校验不等同服务器执行校验。

## 低显存与恢复

默认batch1和串行。共享library的生产锁防止本工具并发提交。切模型调用已安装ComfyUI `/free` 请求卸载并清缓存；该接口由服务器异步处理，具体CPU/GPU驻留以采样日志为准。本工具不修改启动参数，不宣称控制了外部程序显存。

提交前保存任务和request，取得prompt_id立即落盘。超时保持同一ID；网络响应丢失但无法判断是否接受时标记UNKNOWN。仅服务器明确执行失败可重试，最多三次；OOM按16像素对齐降低分辨率，保留改变及资源日志。日志10秒采样，只能报告采样最大值，不保证捕获瞬时峰值。

## 人物一致性与首尾帧

角色候选由用户审批，state version独立保存服装/饰物。普通文生图无法消费参考身份，因此人物镜头只能preview。存在相应参考工作流时，首帧上传批准角色图；多角色要求分别绑定。dual尾帧以上镜首帧为编辑输入，普通VAE图生图不自动视为语义身份编辑。

生成成功证明图片存在，不能证明脸型、动作、道具和构图合格。视觉审核是单独状态。元数据连续性只检查已记录状态，未记录的物理变化不能自动推断；独立随机出图不会被声明一致。正式导出要求当前版本来源匹配、图真实可读、角色审批和视觉检查合格。

## 官方接口与来源

- [ComfyUI服务器路由](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [Z-Image Turbo配方](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)
- [Qwen-Image配方](https://docs.comfy.org/tutorials/image/qwen/qwen-image)
- [Qwen-Image-Edit配方](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit)
- [Skills构建规范](https://developers.openai.com/plugins/build/skills)

本机开发还核对了已安装server.py/main.py与object_info。公开测试夹具仅保留本项目用到的核心节点，去掉个人图片名与视频模型等无关清单。
