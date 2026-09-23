# 突变体-3 飞扑落地特效与冲击音效

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

2026-09-23，按用户批准的方案制作。原有 3 倍伤害、2 秒眩晕、120°/250 cm 命中范围及动作保持。

## 表现与触发

- 真实 `Landed()` 一次性触发地面效果和声音，闪避导致伤害落空时仍保留物理落地表现。
- 冲击波持续 0.32 秒，前方 120°、半径沿用 `PounceImpactRadius`（默认 250 cm）。灰白、低亮度，按落地法线贴地抬高 3 cm，不产生灯光、永久印痕或物理碎块。
- 尘土最多 8 团，远处 4 团，约 0.38–0.52 秒消散。发射位置在扇形内逐点采样地面，并避开墙体、悬空位置和玩家/怪物身体。
- 实际伤害大于零且玩家存活才叠加命中相机效果：0.18 秒的小幅俯仰/侧倾、最长 0.08 秒的低强度提亮降饱和。与已有红色受伤淡入淡出合成，不接管 CameraManager 的 fade 状态。
- 飞行中、普通落地、普通爪击和伤害判定外的玩家不会触发这套命中相机效果。

## 音效选择

采用已有 `/Game/Monsters/HandBrain/Audio/S_HandBrain_slam` 的独立副本 `S_Mutant3PounceImpact`。原始长度 0.52245 秒；运行时音高 1.08–1.14、音量 0.78，从真实落点播放，近场 120 cm、衰减至约 20 m，并启用遮挡降音量/低通。

Khaimera 自带 `Khaimera_Effort_LandHeavy` 是约 1.78 秒的重落地发力声，未混入此次短促砸地反馈。原音频资产不修改。

## 资源来源和实现范围

- Fab：Vefects 的 [Easy Impact Frames](https://www.fab.com/listings/15cb7c95-3220-43fe-8d68-c67c73e83eba)，用户已导入本机工程。
- 复用其 `M_VFX_Shockwave_01` 所引用的冲击波 Noise Texture、Intensity Mask 纹理及匹配采样设置，制作专用 `M_Mutant3LandingWave` 扇形地面材质。源包材质、纹理和演示蓝图均保留。
- 使用项目已有 `UFPSImpactFXSubsystem`，新增 4 个共享冲击波槽；尘土使用原有 24 个槽；总粒子上限仍为 192。音效独立复用 2 个预分配声道，不切断正在播放的尾音。
- 材质、声音在初始化时加载；命中路径没有同步资源加载、动态材质创建或临时粒子 Actor。特效容量不足只丢弃视觉细节，不影响伤害和眩晕。
- 当前接入沿用项目现有单机战斗路线，没有新增网络特效同步。

## 文件与状态

- 原生接入：`Monsters/Mutant3Feral.cpp`、`Monsters/Mutant3PounceCameraShake.*`、`Weapons/FPSImpactFXSubsystem.*`、`Weapons/FPSImpactFXPounce.cpp`。
- 正式资源目录：`/Game/Monsters/Mutant3Meshy/Effects/`。
- 制作源、旧文件备份、源参数记录和落盘回执：`SourceAssets/Mutant3LandingFX20260923/`。
- 正式材质和音效副本已由后台 commandlet 保存，退出码 0；常规 Editor 构建已成功，日志为 `Saved/BuildEditor/build-20260923-223735.log`。完成状态见该目录 `delivery.json`、`assets_saved.json`。初次构建遇到的其他模块编译错误已在并行工作区中修正，本任务未修改这些文件。

按用户规则未启动游戏、录制画面、进行音效试听或运行验收；视觉、听感和玩法由用户测试。
