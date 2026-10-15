# M66 V16 砸地加速与落地停顿

按用户要求保留举臂蓄势，加快出拳下砸，在地面保持 0.5 秒再收势。直接从 V14 可编辑源重采样完整姿态，不改模型、权重、拳形、手腕轨迹或足部支撑关系。

## 同一动作时钟

- 0–1.35 s：保留原蓄势动作与握拳过程。
- 1.35–1.50 s：0.15 s 加速下砸；源动作该段约 0.2833 s，平均约 1.89 倍速度，采用 `u^1.65` 的非线性源时间映射，接近接触时更快。
- 1.50 s：采样原第 98 帧的贴地姿态，释放现有 AOE 冲击波。
- 1.50–2.00 s：拳头保持落地姿态整整 0.50 s，形成受力停顿。
- 2.00–3.8667 s：使用起始速度为零的单调 Hermite 时间映射，从停顿平缓进入收势；原动作终点保留。

465 帧/120 Hz 全骨架烘焙把非线性节奏保存到正式动画。密集帧之间保持线性插值，以避免 Bezier 过冲改变拳头贴地姿态；这不同于整段恒速播放，也没有只调整 `RateScale`。

`M66SlamTiming.h` 的释放时刻同步为 1.50 s、动作结束 3.8667 s。UE 接入时按新时间重新生成拳面采样，用于定位冲击波落点。AOE 的 4 m 半径、0.55 s 扩散、135 物理伤害、2 s 眩晕、6 s 独立冷却及原额外 1 s 决策间隔均保留。主客机继续使用同一服务器动作时间。

## 制作与接入

`author_rhythm.py` → `Authoring/M66_fist_slam_rhythm_v16.blend` / `Export/A_M66_FistSlam_V16.fbx` → `import_motion.py` → `install_character.py`。正式新动画为 `/Game/Monsters/IncineratorBossM66/SlamImpactRhythmV16/A_M66_FistSlam_V16`，原角色与 F6 入口保留。

2026-10-15 已完成：09:43 常规 Editor DLL 构建成功（`Saved/BuildEditor/build-20261015-094310.log`，`Result: Succeeded`）；09:45 后台导入 V16 动画，并保存共用骨架和原角色蓝图。安装进程 36704 正常退出，退出码 0。完成记录为 `Records/native_build.json`、`Records/motion_import.json`、`Records/character_install.json` 和 `Records/install-20261015-094429/`。

原角色已改用 V16 动画与 11 帧落点采样，AOE 参数、横扫、网格与黑烟保留。通过 F6 原 M66 入口重新生成即可体验。未运行游戏、渲染或联机测试，由用户体验。
