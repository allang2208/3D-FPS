# M-07 V19：指定视频的移动参考候选

日期：2026-10-03。工程：`D:/FPS3D/FPSGAME`。

后续状态：用户确认奔跑姿势有所改善后要求掌心朝后，[V20](BlindSupplicantM07PalmArmMotionV20.md) 曾接替两段移动引用。随后用户指出整体姿态仍偏离参考，[V21](BlindSupplicantM07FullReferenceGaitV21.md) 已重制完整两段步态并成为当前引用，重新匹配屈肘、承重与全身联动。本文件记录 V19 原制作与交付。

当前阶段：指定五秒视频已读取，两段移动候选、可编辑源和 FBX 已制作，独立 UE 动画及现有 AI/F6 蓝图引用已在后台实际保存。保存回执为 `SourceAssets/BlindSupplicantM07Meshy20261001/VideoLocomotionV19/ue_video_locomotion_delivery_v19.json`；未运行游戏、渲染或测试，观感由用户体验。

## 参考与动作意图

用户指定 [Yummy Games 演示视频 2:00–2:05](https://www.youtube.com/watch?v=dJ-Ak3X7tiM&t=120s)。已取得仅用于本机动作研究的五秒公开视频，并实际查看连续抽帧；参考资料位于 `VideoLocomotionV19/Reference/`。未取得付费动画包的原始轨道，制作结果属于按视频适配的候选，不能称为原动画直接重定向或精确视频动捕。

该片段为八方向原地 Jog。以前方中央角色的向前移动为主要参考，侧向角色仅辅助理解风格；这些角色不是同一动作的同步多机位。它使用普通人体膝关节、微前倾和弹性承重，骨盆、胸肩随脚步共同运动；双臂半屈、略向外打开，手位偏低，头部相对稳定。用户本次指定的是较松弛的怪物慢跑。

重复轮廓的完整周期约为 32 个视频帧；按公开片段的 24 fps 推断为 1.333 秒，左右步间隔约 .667 秒。该值来自画面周期，不是取得了原动画帧表。视频像素不能直接转换为 UE 厘米、速度或完整三维关节角。

成熟运动基础为本机 Mesh2Motion 固定版本的 CC0 `human-base-animations.glb` 中 `Jog`、`Walk`；其来源清单与缓存保存在 `VideoLocomotionV19/Donor/`。这些供体是完整人形动作基础，不是 Yummy Games 的原始素材。

## 制作与保留范围

沿用 V17 Skin Master 的原 Meshy 几何、UV、V16 肩肘腕权重、V17 髋膝踝权重、83 骨 V11 参考帧。载入制作母版立即切换 `POSE`，保留参考骨长度和绑定平移；第零帧只供参考，导出从第一动作帧开始。膝关节使用 V17 共同带符号解剖铰链；足底支撑和摆臂按实际身体比例适配。

保留原手指局部动作与鳃膜局部呼吸，沿用 V18 接触避让和布料配置。未重导显示网格、模拟代理、贴图、Physics Asset 或 LOD；未改攻击、施法、死亡、冷却、导航及共享 AI。

制作入口：`Tools/BlindSupplicantM07/author_video_locomotion_v19.py`。可编辑源、两段 FBX 和制作清单位于 `VideoLocomotionV19/Move/`。

| 动作 | 导出时长／帧数 | 制作源速度 | 现有 AI 速度 | 预期游戏播放周期 |
| --- | --- | --- | --- | --- |
| SlowWalk | 1.667 秒／51 帧，30 fps | 135 cm/s | 160 cm/s | 约 1.406 秒 |
| Chase | 1.333 秒／41 帧，30 fps | 270 cm/s | 360 cm/s | 约 1.000 秒 |

源速度为按 M-07 原腿长拟合的制作值，并非视频测量速度。现有速度比逻辑分别以约 1.185／1.333 倍播放；追击保留当前 360 cm/s，因此实际游戏比参考画面的原周期更快。支撑脚的后退速度与制作源速度统一，以便播放倍率同步位移；这些是制作与接入参数，不是运行测试结果。

## 接入边界

导入入口为 `Tools/BlindSupplicantM07/import_video_locomotion_v19.py`，仅保存独立目录 `AnimationsVideoMotionV19/` 的 `A_M07_SlowWalk`、`A_M07_Chase` 及现有 `BP_BlindSupplicantM07`。原 V18 动作保留；角色蓝图制作前副本位于 `VideoLocomotionV19/Before/`，保存回执记录旧引用和源速度。

沿用现有速度驱动、走跑相位继承和播放倍率；动作源速度由实际支撑轨迹决定，蓝图保存对应字段。原生 C++ 字段和动画图已有所需能力，本次无需新增代码或构建模块。

已通过 `run_import_background.ps1 -TaskScript import_video_locomotion_v19.py` 的无界面 commandlet 保存两段新动画和原角色蓝图，原生模块无需重新构建。落盘日志为 `Saved/Logs/M07Import-20261003-010753.log`。后台导入会拒绝覆盖正在 PIE 的资产；已有编辑器操作走批次互斥，不主动打开、关闭或重启 UE。

未进行运行测试、验收渲染或性能采样；最终动作观感与接触效果由用户从现有 F6「盲祷者 M-07」入口体验。
