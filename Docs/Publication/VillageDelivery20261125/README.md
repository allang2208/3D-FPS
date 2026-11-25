# 丘陵村庄 · 风车、酒馆与城内地表

工程入口为 `L_ForestPathVillage`，建筑位于其流式村庄子关卡。磨坊的院树常驻，工作院、梁灯和管理员随修复出现。酒馆保留一楼厅堂与厨房，楼上分为四间客房及老板套房。酒馆前庭使用碎石泥路，食槽外端有随营业状态启用的排水痕。城内地表共用一米格点；教堂院子、路肩和墙脚的小片 Forest Floor 采用固定种子离线生成。

## 源码与接入

1. 依据[源码清单](Implementation/files.json)按工程相对路径恢复源码和制作脚本。独立实现位于清单中的 `public` 路径，其中一部分保存在本交付目录，另一些在工程 `Tools/` 和 `SourceAssets/`。公开主线与正式 UE 宿主的森林地图、村庄和角色系统存在版本前置。[宿主文件指纹](Recovery/host-requirements.json)
2. 酒馆、地形和兼容签名的共享宿主使用[按版本排列的差异](Integration/deltas.json)。先比对前置 LF 文本指纹；若宿主已有其他改动，按补丁中的函数合并。磨坊对话同时涉及交互瞄准、控制器发起、服务端距离校验、客户端面板和话题文案。[对话接点](Integration/mill-keeper-hooks.json) · [玩家及管理员装配](Configuration/keeper-and-player.json)
3. 在正式宿主的布局文件中合并[酒馆与院落参数](Configuration/inn-forecourt.json)，保留后续建筑迁址。地面层按[丘陵主题键](Configuration/terrain-theme.json)读取；从本机制作源恢复 16 位高度输入、接触框和材质遮罩。4 个早期分步文件仅留有发布指纹，当前调用位置和已收录的完整制作脚本可用来移植相应行为。[早期指纹](Integration/legacy-source-fingerprints.json) · [现行调用位置](Integration/current-consumers.json)
4. 联机复测入口为 `Review/run_net.py --engine-cmd <UnrealEditor-Cmd.exe> --project <本版隔离项目.uproject> --previous-project <旧版隔离项目.uproject> --out <新结果目录>`，两个宿主分别使用其已编译的模块。复测在隔离宿主中创建新世界、执行真实对话和修复请求，随后重连。路由文件 `Review/walking.json` 供现有 SmithLoftReview 站立通行夹具使用。正式游戏存档独立保存。

## 资产与恢复

NAS 以 `备份/FPS3D/` 为根。[归档清单](Recovery/archives.json)列出三个压缩包的 SHA-256。`ProductionAndVersions.zip` 和 `HostPackageRecovery.zip` 用清单将原路径映射到 `blobs/<sha256>`；`CurrentHostInputs.zip` 按内部工程路径保存当前接入前置。恢复时按所需版本逐项提取，注意正式村庄地图后来还接受了马厩扩建与灯光优化。[正式资产指纹](Recovery/current-packages.json) · [版本条目](Recovery/source-versions.json)

原始参考图、Meshy 输出、Fab／Quixel 授权扫描、角色服装与骨架、贴图、UE 包和编译模块沿用完整本地工程与原许可。三视图、设计图和可编辑原稿保留在各功能的制作源。公开发布包含源码、接入差异、资产指纹和必要的结构化结果，完整运行需要匹配的本机宿主与资产。

## 已有验收及清理

同机 UDP 的 60 毫秒延迟与 2% 丢包条件下，九项检查通过；主客机及碰撞在十二个采样点一致。两条站立路线均走通。原丘陵换图和回收未复现历史析构崩溃，原始内存错误根因仍未证实。新版独占 GPU 帧耗尚待实测。[实测摘要](Evidence/results.json) · [完整范围](../../WorldGeneration/village-delivery-review-20261125.md)

任务宿主、临时操作文件、检测截图与重复版本副本已移入分盘 `trash/VillageDelivery-20261125`。保留了发布回执、结构化验收数字和已采用的制作输入。逐文件原路径、去向、字节数、SHA-256、替代位置以及联接定义位于本机 `ArtProduction/StorageLayout/VillageDeliveryPublication-20261125/`。[清理统计与清单指纹](cleanup-summary.json)
