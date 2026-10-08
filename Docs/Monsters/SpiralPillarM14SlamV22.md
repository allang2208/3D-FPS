# 螺柱 M14 下砸 V22

2026-10-06。按用户要求缩短前摇、加速下砸并增强冲击；被实际伤害命中的存活玩家受到 2 秒眩晕和 5 米击退。

## 动作与声音

| 阶段 | 时间 | 表现 |
|---|---|---|
| 短前摇 | 0–0.35 s | 躯干短暂后蓄，组织与螺柱发出低声绷紧声 |
| 快速下砸 | 0.35–0.55 s | 加速俯砸，保持原 V13 落地点与接触姿态，气流随砸落上升 |
| 命中 | 0.55 s | 单次伤害、眩晕、击退与重击音效共用此时刻 |
| 回弹 | 0.55–0.78 s | 接触处短停两帧、轻微反弹再落稳，保留组织与金属跟随 |
| 恢复 | 0.78–1.70 s | 渐缓起身，衔接原待机／移动 |

旧动作前摇约 0.8 秒、0.4 秒砸落，1.2 秒接触，3.2 秒结束。新动作从最新 V21 母版内的 `A_M14_TrunkSlam_v13` 重排时序，保留已经修好的支撑蒙皮与金属跟随。八根根部支撑每帧继续锁定；没有修改网格、骨架绑定或上一版撕咬。

新音效压缩已有 AudioV01 绷紧前摇，叠加加速气流、湿组织撞击、低频闷响和轻螺柱震荡。沿用现有本地 CC0 素材和合成音，48 kHz 单声道 PCM；制作记录明确 MP3 素材来源，未试听。

## 命中控制

`SpiralPillarM14Slam.cpp::SlamContact` 沿用服务器权威、实际躯干采样、墙体遮挡和每次攻击每目标仅一次的伤害路径。实际扣血且目标仍存活后：

- 复用或创建目标持有的 `UPlayerGuardBreakComponent`，执行 `Apply(2.f)`；沿原有计时器和拥有者复制同步输入锁与眩晕状态，结束时恢复。
- 复用 `UFleshHandPushComponent`，沿远离螺柱的水平向量推移 `500.f` cm。沿原有 0.16 秒衰减位移、角色碰撞和身体受击表现处理；遇到阻挡停止，不穿墙保证凑足距离。
- 完全格挡、弹反打断、无敌、死亡不附加控制；冰墙继续按原规则受伤，不施加角色控制。

没有增加新的反射成员、原生类或常驻 Tick；控制值位于该下砸实现的 `M14SlamControl` 命名空间。伤害倍率、攻击范围和冷却保持现有蓝图值。蓝图只修改 `trunk_slam_clip`、`trunk_slam_sound` 与 `slam_contact_seconds`。

## 制作与保存

- 时序：`Tools/SpiralPillarM14/slam_v22.json`。
- 动画：`author_slam_v22.py`；音效：`author_slam_audio_v22.py`。
- 导入：`import_slam_v22.py`；后台／现有编辑器入口：`Import-SlamV22.ps1`。
- 制作母版：`SourceAssets/SpiralPillarM14Meshy20261004/ProductionV22/Authoring/M14_ImpactSlam_v22.blend`。
- 目标动画：`/Game/Monsters/SpiralPillarM14/Animations/A_M14_TrunkSlam_v22`。
- 目标音效：`/Game/Monsters/SpiralPillarM14/Audio/SlamV22/S_M14_TrunkSlam_v22`。
- 原蓝图：`/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14`。

动画与 WAV 已导出；Editor、Game 原生构建均已完成（退出码 0）。新动画、音效、骨架及原蓝图已通过无界面 Python commandlet 实际保存，退出码 0、`ue_revision.json` 为 `complete: true`。构建和资产保存记录位于 `ProductionV22/Records/build_FPSGAMEEditor.json`、`build_FPSGAME.json`、`ue_revision.json`，导入日志为 `Saved/M14SlamV22/import-commandlet-20261006-215414.log`。保存前已备份蓝图及骨架至 `ProductionV22/Before`。

未启动游戏、未进行运行测试、试听或渲染，由用户体验确认。
