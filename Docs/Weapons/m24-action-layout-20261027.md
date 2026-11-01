# M24 全动作运行时位置修正

接替 `m24-hold-20261027.md` 的视口检查结论。此前 11 张固定相机离线取样只证明
保存资产能在指定变换下显示，未覆盖游戏中的动作锚点、相机和过渡，不能作为
整套第一人称动作的合格依据。

## 原因与范围

M24 使用通用 M4 动作状态机，但原 `UpdateViewmodel` 将其错误纳入 M4 动作构图。
开火拉栓、换弹、检视、近战期间，`M4ActionFramingAlpha` 将校准腰射位置
`(32.512, 13.984, -25.732)` cm 插值到 `(10, 0, -5)` cm，向眼睛拉近约 22.5 cm、
抬高约 20.7 cm。开火拉栓虽然处于 Idle 状态，仍由 `IsRevolverFireActionPlaying`
进入这条路径。

修正只让 M24 保持自己的动作构图；同一刚体变换同时作用于枪、双臂和配件。
保留 Hold20261027 的 V9 手臂、81 个关节修形、Repair20261027 的枪体材质和
可拆配件。运行时位置修正不重新缩放或重新导入网格；随后发现的拉栓手指接触
问题单独重制三段动作，见下文。

## 动作安排

| 场景 | 动作/运行时职责 |
| --- | --- |
| 待机、行走 | idle 呼吸循环 + 现有移动起伏 |
| 装备 | equip，结束回到相同待机 |
| 腰射 | fire 内含右手拉栓，机械事件跟随原 source time |
| 普通换弹 | reload，拆弹匣、装入、就位后回待机 |
| 空仓换弹 | reload_empty，换弹后接拉栓 |
| 中断拉栓恢复 | reload_empty 的拉栓尾段，从 source 1.8 s 恢复，不重复换弹匣或消耗弹药；保留 cycle 资产但运行时不引用它 |
| 瞄准 | 独立静态 aim + 瞄点解算 + 6x 光学显示 |
| 检视 | inspect，恢复同一持枪姿势 |
| 枪托近战 | quick_melee，恢复同一持枪姿势 |
| 冲刺与停跑开镜 | idle + M24 右侧持枪位置 `(6,9,-11)` cm、旋转 `(30,8,-10)` deg，保留原有起伏和 ADS 插值 |

装备动作自带从画面下方抬枪的完整入场和同一待机收尾，播放期间保持 authored
pose 权重 1，避免再从可见待机混入导致先下沉、再抬枪的双重入场。

## 本轮检查方法

`SourceAssets/M24ActionLayout20261027/run_review.ps1` 在命名互斥锁内运行独立
`-game -RenderOffscreen` 进程，使用 `M24ActionAudit_<label>` 临时档案和独立 UserDir。
`FPSGAMECharacterM24Review.cpp` 只在显式 `-M24ActionAudit` 参数下工作，按真实
输入入口推进状态机，记录实际视口画面、相机、动作源时间、混合权重和视模变换。
每秒 30 帧，覆盖 14 段流程及恢复，不是固定锚点的离线骨架预览。

首次 before 录制被项目启动菜单暂停，未产生有效画面，不算检查证据。
后续启动器使用项目已有 `-SkipStartupMenu` 入口。

第一轮 `after_v1` 实际记录 948 帧、14 段流程，缺图 0。所有帧的通用 M4
动作构图权重均为 0；开火消耗一发，普通/空仓换弹均补回 5 发，独立拉栓
保持 5 发且从 source 1.8 s 的尾段开始。实际行走速度 450 cm/s、冲刺 700 cm/s。
该轮未包含 Slate 界面，所以只用于枪和手臂轨迹检查，不用于瞄准镜显示结论。

全帧复核后补充了 M24 冲刺右侧构图和装备入场权重，第二轮连同瞄准镜 UI
一起记录。构建首次因并行新增的 `ColdSteelIncineratorStorage` 使用
`FJsonObjectConverter` 而缺少链接依赖失败；仅补上 FPSGAME 的私有
`JsonUtilities` 依赖。该轮构建成功：`Saved/BuildEditor/build-20261027-152139.log`。

## 高清接触复核与动作重导入

第二轮记录 896 帧、缺图 0，确认光学界面工作；常规 HUD 在 960×540 下占比过大。
第一次请求 1080p 被窗口自动限制为 888×500，该轮不作为高清证据。启动器随后
加入引擎原生 `-ForceRes`，实际截图达到 1920×1080。

高清复核在开火拉栓 source 0.93 s 发现 V9 指尖穿进瞄准镜后端。根据实际枪栓
把手网格测量，保持枪械和机械部件动作不变，将右手拉栓接触段沿把手坐标系
调整；以 fire 第 28 帧的枪根坐标表示为 `(3.0,-1.2,2.5)` cm。进入抓握时渐入、
归位收手时渐出，并重新解算右臂两节 IK 和 twist01 100% / twist02 50% 的扭转。
保留指骨相对姿势、所有 V9 网格数据和机械事件时间。

- 可编辑源：`SourceAssets/M24ActionLayout20261027/M24_ActionLayout_Editable.blend`
- 制作入口：`author_bolt_grip.py`；实际测量：`bolt_grip_measure.json`
- 导出：`Exports/Animations/` 下 fire、reload_empty、cycle 三段 FBX
- 导入：`run_import.ps1` / `import_grip.py`；结果：`grip_import_receipt.json`
- 已保存：`/Game/Weapons/M24/ActionLayout20261027/Animations/A_M24_{fire,reload_empty,cycle}`
- `M24WeaponAssets::AnimationPath` 只将这三段路由到新目录，其余动作继续使用 Hold20261027。

## 最终交付与复核结果

最终构建成功：`Saved/BuildEditor/build-20261027-154355.log`。三段动作已通过后台
导入保存，`grip_import_receipt.json` 的 `complete` 为 true；实际运行时记录已使用
新 fire / reload_empty 资产。修订后的 cycle 资产也已保存，仍保留为独立源动作。

最终录制位于 `SourceAssets/M24ActionLayout20261027/grip_final/`，`runtime.json`
记录 `complete=true`、14 段流程、896 帧；`summary.json` 记录缺图 0，实际分辨率
1920×1080。`M24_full_actions.mp4` 为约 29.87 秒、30 fps 的完整连续画面，包含
实际瞄准镜 UI；`Sheets/*_all_*.jpg` 保留所有采样帧，`Frames/` 保留高清原图。

逐帧检查覆盖装备、待机、腰射拉栓、普通换弹、开镜、镜内开火拉栓、退镜、空仓
换弹、拉栓恢复、检视、枪托近战、行走、冲刺及停跑开镜。该次录制中：

- 通用 M4 动作构图权重全程为 0，未再出现整枪因动作锚点切换而推到眼前遮挡视野。
- 冲刺持枪留在右侧，装备从下方抬入，动作结束恢复同一待机位置。
- 新拉栓抓握在腰射、空仓换弹和恢复尾段的高清接触帧中避开后端镜片；枪栓轨迹及原事件时序保留。
- 开镜、镜内开火、退镜及冲刺后开镜均保留光学界面和恢复过程。
- 腰射、瞄准开火各消耗 1 发；普通/空仓换弹回到 5 发；拉栓恢复保持 5 发。

本轮按用户要求完成运行时视觉复核，尚未获得用户视觉验收。录制使用 `-nosound`，
不包含音效试听或联机结论。未打开编辑器；导入、构建及离屏运行均在后台完成。
