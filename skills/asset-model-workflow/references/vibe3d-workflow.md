# Vibe3D 制作与后处理（2026-09-19）

用户已同意将 Vibe3D 加入现有模型与 UE 接入工作流。它通过 UE 原生 MCP 暴露 ModelingService，是编辑器内的程序化建模工具。

## 分流

- 尺寸和结构明确的楼梯、栏杆、箱体、管件、建筑模块与机械零件：优先考虑 Vibe3D 直接制作。已有参考与尺寸足够时，不强制补生成三视图或跑 5080；外形设计不明确时仍先确定参考。
- 生成模型：沿用用户指定生成器及已选母版，Vibe3D 用于局部修整、减面、UV、烘焙、碰撞和 LOD。只执行任务需要的步骤，不自动全网格重拓扑或重铺 UV。
- 枪械配件：可做精确接口、开孔、倒角、机械分件与刚性骨骼绑定；枪匠、挂点、ADS、装备和存档接入仍走武器技能。
- 手臂与怪物：骨骼/权重工具仅作辅助；成熟蒙皮、动作参考、接触时序、Control Rig/Blender 与战斗接入继续走对应技能。
- PCG 负责排布模块，Vibe3D 负责模块几何。插件的体素操作不作为 FPSGAME 实时挖地、破坏或玩家建造系统。

## 接口与执行

项目桥：D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1。
端点配置：Config/DefaultEditorPerProjectUserSettings.ini，当前为 http://127.0.0.1:8000/mcp 。
需要调用时读取实际接口；过去工具发现成功不表示当前服务在线。

桥调用方式：
- -DescribeToolset Vibe3D.ModelingService：读取当前接口说明。
- -Tool call_tool -ArgumentsFile <JSON文件>：外层参数含 toolset_name、tool_name，具体内层字段以当前工具 schema 为准；tool_name 使用裸名，不重复工具集前缀。
- -BatchFile <JSON文件>：顺序执行批量任务，批量不是事务。

编辑器 Python 等价入口为 unreal.ModelingService.<snake_case>(...)；需要未封装 GeometryScript 操作时，用 get_dynamic_mesh(handle) 获取网格。

制作流程按任务选择：创建/加载网格 → 几何编辑 → 所需 UV/烘焙 → 保存 StaticMesh/SkeletalMesh → 所需碰撞/LOD → 领域接入。
处理每次操作返回的 success/message 和资产路径；失败时停止依赖该结果的写入。读取完成当前编辑所需的尺寸、材质槽、接口签名属于制作资料，不扩展成验收。

- 使用厘米、Z 向上，按实际消费者确定轴向与 pivot；旋转使用 unreal.Rotator(roll=..., pitch=..., yaw=...)。
- 拓扑变化后重建后续需要的命名选区。保留既有材质槽、UV、硬边、权重及功能孔洞；修整范围由任务决定。
- 网格 handle 是编辑器内临时状态，不是已保存资产，也不随 MCP 重连自动恢复。记录本任务创建的 handle，完成后只 release_mesh 自己的 handle；共享编辑器不调用 release_all_meshes。
- 修改已加载资产在编辑器进程内完成。写入前读取目标当前状态与归属，避免覆盖并行修改；用明确的候选/修订路径承接新版本。
- 多会话可使用 MCP，但同一资产写入、编译、PIE 按现有 UE MCP 并发规则协调。服务断开时记录阻塞，不自行杀编辑器、重启或重复提交结果不明的写入。
- 作者参数与脚本放 SourceAssets/<任务>/ 或既有工具目录；交付注明源资产、输出路径和接入引用。无需为了接入本流程批量替换旧资产。

## 文档与测试边界

API 细节优先读取当前安装插件的 Content/Skills/modeling/SKILL.md 和 Source/Vibe3D/Public/Vibe3D/UModelingService.h，当前安装目录：
E:/Program Files (x86)/UE_5.8/Engine/Plugins/Marketplace/Vibe3Dd7b2fe90b7d0V1/ 。
路径随安装版本变化时从实际插件目录定位。官网：https://www.vibeue.com/vibe3d 。

插件自带文档中的默认截图、逐阶段验收、测试套件和示例 release_all_meshes 不直接继承为项目规则。遵守用户 2026-09-12 全局要求：默认只制作、必要构建、保存与授权接入；仅在明确要求时测试、截图、渲染或验收。未测试如实交由用户测试。接口成功返回不代表视觉、游戏或落盘验收通过。

历史 Vibe3D 几何问题沿用主技能“在运行中的编辑器里做资产”记录，不把一次案例参数套用于所有模型。插件指南按需读取，不自动执行 GenerateAgentConfig 覆写项目规则。
