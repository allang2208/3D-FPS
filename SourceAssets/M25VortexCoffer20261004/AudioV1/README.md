# 涡电匣 M-25 音效 V1（2026-10-05）

本轮授权：为 M-25 涡电匣制作并接入音效。策略为**优先复用本地素材**：有机层全部来自 M-10 已筛选的 CC0 freesound 预览（`../../M10ChenXia20261003/AudioScout`），来源与对应表在 `Records/audio_source.json`。

**V2 写实化（2026-10-07，用户反馈电声太卡通）**：原合成的正弦扫频 zap、节拍化噼啪、纯合成雷裂是卡通感主因，全部替换为 CC0 实录素材（`Scout/`）：follytowers 特斯拉线圈放电 415960/362975（电弧嘶鸣床、放电瞬态、循环底噪）与 cognito perceptu 真雷裂 347853（雷枪释放）；蓄力只保留低增益电容啸叫底层、主体改为实录嘶鸣渐强。TRP 616992 已下载备用未用。

## 产出与接入

| 资产 | 时长 | 内容 | 接入点 |
|---|---:|---|---|
| S_M25_Idle | 3.6 s 循环 | 腹鸣共鸣体床 + 96 Hz 电极嗡鸣 + 稀疏电火花 | `IdleVoice`（body_05）存活常响 |
| S_M25_Crawl | 2.6 s 循环 | 慢速湿触手拖行 + 4 个足垫闷点 + 微火花 | `CrawlVoice`，着地且速度 >4 cm/s |
| S_M25_Crackle | 4.0 s 循环 | 特斯拉线圈放电嘶鸣床（实录）+ 100 Hz 嗡鸣 + 两次真实放电突刺 | `BackElectric` CrackleVoice（socket_electric_00），音量随电弧峰值调制 |
| S_M25_Bite | 0.8 s | 短嘶起手 → 0.33 s 合咬 + 电火花 + 湿尾 | Bite `OnRep_State` 激活时 socket_maw 播放（接触窗 0.30–0.38 s） |
| S_M25_Charge | 0.6 s | 尖锐电流蓄力：细长高频啸叫（1.5k→5.4k Hz）+ 冠状放电嘶鸣渐强（对位 0.55 s 蓄力） | Magic 进入 Lightning 相位，电极位置播放 |
| ~~S_M25_LanceCharge~~ | 1.7 s | （已退居备选）雷枪蓄力现复用玩家 `S_ThunderLanceCharge` | BP CDO `lance_charge_sound` 改绑玩家资产 |
| ~~S_M25_LanceRelease~~ | 1.8 s | （已退居备选）雷枪释放现复用玩家 `S_ThunderLanceDischarge`（炮口 1.0）+ `S_ElectricCast1`（终点尾音 0.8） | BP CDO `lance_release_sound` 改绑玩家资产 |
| S_M25_Hit | 0.75 s | 湿肉受击 + 火花迸溅 + 56 Hz 闷击 | `StartHitPresentation`（复制镜像各端都播） |
| S_M25_Death | 3.0 s | 下行呻吟 + 1.35 s 塌落 + 电极断电衰减 | `OnRep_Death`（权威端与各客户端都播） |

## 代码改动

- `VortexCofferM25.h/.cpp`：`M25|Audio` 九个 `EditDefaultsOnly` 声音属性；`IdleVoice`/`CrawlVoice` 组件（body_05，衰减 1400/1500 cm）；`Tick` → `UpdateLoopAudio` 按存活/着地/速度启停两条循环；`OneShotAttenuation` 供组件调用。
- `M25Damage.cpp`：`StartHitPresentation` 在 socket_maw 播受击声；`OnRep_Death` 在 body_05 播死亡声。
- `M25BiteComponent.cpp`：`OnRep_State` 激活边沿在嘴部播咬合声（服务端本地调用覆盖单机/监听服）。
- `M25BackElectricComponent`：CrackleVoice 挂 socket_electric_00，随放电可见性启停、音量随电弧峰值。
- `M25MagicComponent`：ChargeVoice 随 CastState 相位边沿起停（打断即停）；`MulticastImpact` 雷枪用 LanceReleaseSound 区分普通闪电。
- 2026-10-07 雷枪特效换新：蓄力聚气从 `NS_ThunderCharge`（旧通用蓄力）换为 `LanceRay/NS_ThunderLanceGather`；释放新增 `NS_ThunderLanceMuzzle` 炮口爆发（多播、沿束方向）；雷枪释放恒走 `InitializeColumn` 射线柱，删除 `NS_LightningChain` 旧电弧兜底（普通闪电仍走 InitializeArc）。新增 `LanceGatherAsset`/`LanceMuzzleAsset` 两个 VFX 属性并入异步加载与 `CanAttack` 门控。
- 2026-10-07 二次补齐（用户反馈特效无变化）：补上新雷枪最具标志性的**虹膜层**——蓄力期在电极前方生成 `SM_ThunderLanceIris` 虹膜光斑（随充能 9→25 放大、沿瞄准朝向、Strength/FirePower 联动，玩家雷枪同款配方），释放瞬间生成炮口虹膜闪（0.16 s 内 26→230 扩放衰减）。此前只有聚气粒子和光束本体（光束 10/5 已是射线柱），变化不明显即因虹膜缺失。
- 2026-10-07 雷枪音效同款（用户指定）：雷枪蓄力/释放声音改绑玩家资产——蓄力 `S_ThunderLanceCharge`（ChargeVoice 起停逻辑不变）、炮口 `S_ThunderLanceDischarge`（音量 1.0）、终点尾音 `S_ElectricCast1`（0.8，新增 `LanceTailSound` 组件属性并入异步加载）。怪物自制 `S_M25_LanceCharge/LanceRelease` 保留在 AudioV1 作恢复路径，不再绑定。
- 2026-10-07 全面复用（用户反馈仍不对）：对照玩家 `FireLanceBody`/`UpdateChargeVisual` 补齐剩余层——蓄力期 authority 每 ~130 ms 生成内向电弧触手汇聚电极（InitializeArc 复制到各端）；释放新增 4 条绕柱缠绕电弧（Segments 26、Jitter .042）、6 条垂直炮口的径向扇形电弧、终点 2/3 条残余散射电弧（撞墙沿墙、落空回锥）；聚气特效提到玩家版 1.6 倍缩放。至此 M25 雷枪 = 玩家版全套：Gather 聚气 + 虹膜光斑 + 汇聚触手 + 射线柱 + 绕柱电弧 + 炮口扇形 + 虹膜闪 + 末端散射。

专用服务器全部跳过（`GetNetMode()!=NM_DedicatedServer`）。伤害、动画、冷却、复制时序均未改动。

## 制作与导入

- `prepare_audio.py`：确定性切片/变调/分层 + 程序电声合成，输出 `Wav/` 44.1 kHz 单声道 PCM16；循环接缝 wrap 跳变 <0.0011。
- `import_audio.py`：commandlet 导入 → `/Game/Monsters/VortexCofferM25/Audio/AudioV1`，Idle/Crawl/Crackle 置 looping、全部 FORCE_INLINE；9 个声音写入 `BP_VortexCofferM25` CDO；元数据标签 `M25.AudioRevision=M25AudioV1_20261005`；`asset_receipt.json` 记录保存。
- `finish_production.ps1`：沿用批次互斥（等编辑器/构建空闲 → Editor/Game 构建 → mutex 内 commandlet）。

## 状态

2026-10-05 完成：5 个 M25 源文件编译通过、双 target 整编成功（并行武器线修复后）；9 个 SoundWave 落盘 `/Game/Monsters/VortexCofferM25/Audio/AudioV1`（Idle/Crawl/Crackle 置 looping、FORCE_INLINE），`BP_VortexCofferM25` CDO 写入 9 个声音引用并保存（`asset_receipt.json`/`delivery.json`）。

2026-10-07 V2：全部 9 条 WAV 以实录电声重写，导入器改为"删旧资产→重导"（所有权校验保留），9 个 SoundWave 重存、CDO 重绑、回执更新。未做运行或验收测试，游戏内试听从用户处确认——重点听 Crackle 嘶鸣床与雷枪释放的实录质感是否消除卡通感。
