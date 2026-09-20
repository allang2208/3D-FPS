# 冲刺下劈：双臂伸展、竖向扰动与冲击 V2

用户本轮要求双臂自然伸直、空间扰动竖直向下，并加强打击感和屏幕冲击。在前一版十字镐参考动作上修改，没有恢复旧 V52 抬臂方案。

## 动作

普通柄、长柄各自保留原握点和手指。举顶握持组略向前，减少耸肩；下劈落点也向前送出，让双臂在工作阶段更舒展。两侧肩肘使用同一个可达约束：目标为保留约 24° 余量的软伸展，肩点最多额外调整 5.5 cm；整组持握遇到手臂长度上限时回投，不拉长骨骼。该角度是作者求解目标，未作为实机测量或验收结论。

- 0–0.60 s 抬举，0.60–1.11 s 加载与保持。
- 1.11–1.31 s 加速下劈，1.31–1.39 s 保持落点 80 ms。
- 1.39–1.50 s 带出，之后回收至 2.60 s。
- 原 1.22–1.40 s 命中窗、攻击倍率和伤害规则保持不变；落点停顿是动画姿态保持，不使用全局时间缩放。
- 剑专有的 Blade_Base/Blade_Tip 标记随 WPN_root 同步烘焙；矿镐参考没有这两条剑用轨道，不能留在待机世界位置。

作者源：`author_overhead.py`；两版可编辑源、120 Hz FBX 和关键帧 JSON 在 `Standard`、`LongGrip`。原前一版作者源保留在上级目录。

## 空间扰动

新增专用 `SM_RuneRift_Overhead`，不再用斜向 Slash1 扰动带。中心线保持竖直，宽度从两端向中部渐宽；UV.x 从顶端向底端递增，驱动已有扰动材质依次揭示。网格高 1.70 m、最大宽 0.38 m、进深 0.88 m。

运行时在稳定瞄准平面中冻结起点，忽略奔跑视模残余滚转及镜头冲击；沿该平面的向下方向漂移。扰动在接触窗起点开始，在 1.31 s 落点完成揭示，再用 0.26 s 消散。折射强度使用 0.16，仅作用于冲刺下劈，普通斩击、重击与突刺仍选择原效果。

作者源：`author_rift.py`、`Overhead_VerticalRift_Editable.blend` 与 FBX。运行资产：`/Game/Weapons/AzureRunesword20260913/SprintOverhead20260920/SM_RuneRift_Overhead`。复用原 `WristRiftV3/M_RuneRift` 材质，没有改动共享材质图。

## 镜头与声音

`Source/FPSGAME/Weapons/RuneSwordOverheadFeel.h` 提供专用镜头节奏：举顶缓慢抬视线、出手加速下压、落点一次下顿和约 0.16 s 衰减余震，随后平滑回正。纵向运动为主，不再沿普通斩击横向转身。确认命中额外增加短时冲击，单次挥击只触发一次，冲刺下劈的致命一击也触发；继续服从现有镜头舒适度缩放。

下劈挥动音略增强，命中音量从普通斩击的 0.65 改为 0.95、音高改为 0.86，复用现有音源。其他攻击声音参数不变。

接入位于 `RuneSwordComponent.cpp` 的镜头分支、扰动选择和命中反馈；没有改变 UObject 布局。必要构建使用当前编辑器 Live Coding，编译结果与游戏效果分开记录。

## 交付状态

两条动画及新扰动网格通过项目 MCP 桥导入保存，回执为 `import_receipt.json`；前一版动画备份在 `Before`。源码编译结果见 `compile-result.txt` 与本轮工程记录。未启动 PIE、运行测试或追加新动作验收渲染，实际姿态、扰动可读性和冲击强度由用户试用。

构建收尾：首次 Live Coding 的 C++ 编译成功，但应用补丁时触发 `UObjectHash.cpp:650` 错误，不能记为热更新成功。随后观察到项目常规 `FPSGAMEEditor Win64 Development` 构建已经完成，`Saved/BuildEditor/build-20260920-205646.log` 明确包含 `[81/101] Compile RuneSwordComponent.cpp`、基础 DLL 链接和 `Result: Succeeded`，耗时 48.21 s。当前编辑器进程已加载 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（20:57:34 产物），因此没有再重复退出或编译。汇总见 `build-status.json`；这是必要构建记录，不是游戏测试结果。

整理记录：本文的 `Before/` 旧覆盖快照已移至 `trash/dual-melee-overhead-retired-20260920/SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/Before/`；恢复以 `Docs/Rejected/dual-melee-overhead-retired-20260920.json` 为准。保留源与最新安装顺序见 `Docs/Weapons/dual-melee-overhead-publication-20260920.md`。历史回执不改写为本次测试结果。
