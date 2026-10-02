# 武器、手臂与待机呼吸整理发布（2026-10-03）

本次按用户授权从 `D:/FPS3D/FPSGAME` 精确发布本对话原创源码、制作配方和经验：裂角护手连续 UV 与剑身金属适配、近战雨天湿润、M16 左指中立绑定、残留 M4 机瞄可见性、成品怪物待机呼吸（排除盲祷者）、枪械检视分类、空手交替出拳，以及撞门 0.25 秒停顿。已经在此前 main 中的手臂和控制器改动不重复提交。

## 归档

被用户否定的 M16 首次位置修正共 8 份脚本、作者清单和可编辑输出已移入 `trash/weapon-arms-publication-20261003/`，无破坏性删除。原路径、目标、大小、SHA-256 与原因见 [归档清单](../../SourceAssets/WeaponArmsPublication20261003/archive-manifest.json)。先前撞门废案已归档到 `trash/fps-arms-door-20261002/`，本次不重复移动。

保留旧八份位置补丁和 `installed.json`，因为 M16 NeutralBind 用它们核对之前已装位置和包哈希；保留护手连续 UV 的 Blend、`surface_transfer.npz`、撞门 V8 姿态及其上游输入，因为当前作者配方仍读取。`Before`、诊断脚本和回退包不因名字旧就判为废案。trash 和完整资产数据留在本机。

## 源码与完整内容恢复

- 护手：恢复合法高地剑源贴图与 `ClovenSurface20261002` 连续 UV 制作输入，生成 `BladeMetal20261002` 四路同源金属贴图与材质副本。正式安装指定 `install_background.ps1 -Script <BladeMetal20261002/install_blade_metal.py 的绝对路径>`；默认旧安装入口会装回上一轮独立金属。中央宝石和特殊槽保持。
- M16：恢复公共 V7 与八个网格的合法 native/geometry 输入，再走 `M16Repair20261002/NeutralBind` 的 19 根左指 mesh reference 旋转和匹配几何修复。后续 `M16SprintDoorWrist20261002` 腕部／奔跑制作已经另行发布，恢复顺序仍须保留其后续改动；本轮指骨修复不是覆盖全部 M16 后续工作的入口。
- 湿润：恢复六类近战原材质和改件，运行 `MeleeRainWetness20261002/install_wetness.py` 生成母材质湿层及 `/Game/Weather/MeleeWetness20261002/DA_MeleeWetMaterials`。公开原生扫描和 MID 复用代码；UE 材质、贴图、备份和保存回执在本机。
- 空手拳击：恢复 `UnarmedIdle20261001`／`UnarmedLocomotion20261001` 合法原生手臂和完整姿态，以及 `StaffQuickCombat20261001` 左拳供体、既有法杖步态／右臂制作输入。由 `UnarmedPunch20261002/author_punch.py` 生成本机 `UnarmedAuthoredPunch20261002.h`，`save_editable.py` 保存左右两个 take。该密集骨骼表与 Blend 不公开；源码拉取后须先恢复生成表。
- 撞门：当前 revision `2026100212` 的起势 0.06 秒、保持 0.25 秒、统一事件 0.31 秒、恢复 0.197 秒、总长 0.507 秒。保留 V8 完整护拳输入，重新生成本机 `DoorPushAuthored20261002.h` 和可编辑 Blend。用户完整撞门音频保持本机，不继承旧候选音效的 CC0 声明。
- 怪物呼吸：发布独立呼吸组件及六个基类默认组件接入，不创建或覆盖动画资产；当前工作区后续枪击反馈与尸体／联机改动留给其所属任务。GitHub 方法及许可链接见 [待机呼吸](../Monsters/idle-breathing-20261002.md)，实现没有复制 GPL 插件代码。

本地 `Multiplayer/ColdSteelPlayerState.cpp` 属于尚未发布的并行联机重构。本轮仅将拳击声明、空手资格、频率／距离与权威伤害的原创增量保存为 [服务端接入补丁](../../SourceAssets/WeaponArmsPublication20261003/unarmed-server-integration.patch)，没有把整个联机目录夹带入 main。该补丁须在匹配的联机源发布后接入，不是 main 当前可直接应用的独立功能。`TransitLoadingSubsystem.cpp` 的地址重载编译修正嵌在该任务新代码中，也继续保留本机。

## SKILL 与发布边界

手臂、武器、天气和怪物的对应 SKILL 已补入指骨绑定、附件生命周期、检视取消归属、左右拳迁移与单时钟、湿润 MID 复用、待机呼吸和撞门重定时经验；个人技能目录和仓库镜像同步。本次只暂存本轮语义片段，保留共享文件里的其他修改及原暂存内容。

公开原创 C++、Python／PowerShell 配方、文档和归档元数据；不公开 UE 包、完整绑定／顶点／姿态 JSON、密集生成头、供体采样、贴图、Blend、音频、DLL、日志或桥回执。完整工程的依赖见 [资源恢复](../AssetSetup.md)。

本次只执行用户要求的仓库整理和推送前检查：授权 origin／main、全部待推提交、完整暂存差异、空白、文件大小、敏感信息及许可。没有重新构建、打开 UE、运行游戏或追加测试。此前正式 Game／Editor 后台构建与资产落盘记录保持在本机，最后 0.25 秒撞门构建已包含检视分类和空手拳击。发布内容与本机完整构建范围不同，不能据此前构建宣称这个公开快照已独立构建或实机验收。

[发布文件清单](../../SourceAssets/WeaponArmsPublication20261003/published-files.json) · [接入边界](../../SourceAssets/WeaponArmsPublication20261003/runtime-handoff.json)
