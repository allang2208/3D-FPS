# 螺柱 M-14 音效 V01（2026-10-05）

螺柱此前**零音频**。按"优先复用"策略：有机层全部来自 M-10 已筛选的 CC0 freesound 预览（`../../M10ChenXia20261003/AudioScout`）；金属硬件层（铆栓铿锵、接缝吱嘎、螺栓震颤）全部本地 numpy 程序合成，与湿组织层叠加对应"机械螺栓+湿组织"的身体设定，无新增许可。来源记录在 `Records/audio_source.json`。

## 产出与接入

| 资产 | 时长 | 内容 | 接入点 |
|---|---:|---|---|
| S_M14_Idle | 3.6 s 循环 | 湿组织腹鸣 + 柱体摇晃吱嘎 + 稀疏铆栓响 | `IdleVoice`（spine_01）存活常响 |
| S_M14_Crawl | 2.6 s 循环 | 八根趾拖行刮擦 ×8 + 接缝震颤 | `CrawlVoice`，Crawl/Returning 着地且速度 >4 |
| S_M14_Bite | 1.15 s | 扑咬前奏 → 0.86 s 合咬 + 金属咬合 + 湿尾 | PresentState Bite，mouth_socket（对位 BiteContactSeconds=0.86） |
| S_M14_Spit | 1.3 s | 黏液咕哝蓄力 → 1.10 s 压射 + 湿嘶 | PresentState Spit（对位 SpitReleaseSeconds=1.10） |
| S_M14_SpitImpact | 0.8 s | 毒液溅落 + 腐蚀嘶 + 滴落 | `M14MucusProjectile::ShowImpact` multicast 命中点 |
| S_M14_TrunkSlam | 1.5 s | 金属吱嘎蓄力 → 1.20 s 柱体砸地 + 铆栓震响 + 地鸣 | PresentState TrunkSlam（对位 SlamContactSeconds=1.20） |
| S_M14_Whirlwind | 3.3 s | 0.55 s 蓄势 → 六圈旋转呼啸（2.86 rev/s 双瓣调制）→ 0.65 s 收势 | PresentState Whirlwind（对位 M14WhirlwindMotion 常量） |
| S_M14_Hit | 0.7 s | 湿击 + 硬件铿锵 | `StartHitPresentation`（Combat 复制镜像各端播） |
| S_M14_Death | 2.6 s | 失谐呻吟 → 组织瘫落 → 1.45 s 起三声五金坠地 | PresentState Dying（软体塌落路径） |

未做音效：SweepLeft/Right（代码注释明确"rejected root sweeps are no longer selected"）、Turn 转向（无独立状态，由循环层覆盖）。

## 代码改动

- `SpiralPillarM14.h/.cpp`：`M14|Audio` 八个 `EditDefaultsOnly` 声音属性 + `IdleVoice`/`CrawlVoice`（spine_01，衰减 1500/1700）；`PresentState` 顶部按复制状态边沿播一次性；`Tick` → `UpdateLoopAudio` 启停两条循环；`StartHitPresentation` 播受击；`OneShotAttenuation` 辅助。
- `M14MucusProjectile.h/.cpp`：`ImpactSound`（ctor FObjectFinder 引用 AudioV1 资产），`ShowImpact` multicast 在命中点播溅落声。
- 专用服务器全部跳过；伤害、动画、软体死亡、复制时序均未改动。

## 制作与导入

- `prepare_audio.py`：48 kHz 单声道；循环接缝 wrap <0.0001；咬合 RMS 峰值 0.82 s（20 ms 窗口分辨率，落在 0.86 s 接触窗）。
- `import_audio.py`：commandlet 导入 → `/Game/Monsters/SpiralPillarM14/Audio/AudioV1`；Idle/Crawl 置 looping、全部 FORCE_INLINE；8 个声音写入 `BP_SpiralPillarM14` CDO；元数据 `M14.AudioRevision=M14AudioV01_20261005`。
- `finish_production.ps1`：批次互斥（等编辑器/构建空闲 → 双 target 构建 → mutex 内 commandlet）。

## 状态

2026-10-06 完成：双 target 构建通过、9 个 SoundWave 落盘 `/Game/Monsters/SpiralPillarM14/Audio/AudioV1`（Idle/Crawl 循环、FORCE_INLINE），`BP_SpiralPillarM14` CDO 写入 8 个声音引用（`asset_receipt.json`/`delivery.json`）。`M14MucusProjectile` 的 `ImpactSound` 走 ctor FObjectFinder，无需绑定。未做运行或验收测试，游戏内试听从用户处确认。
