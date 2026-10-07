# 伏窥者 M-08 音效 AudioV01（2026-10-06）

为伏窥者补齐本体声音体系。沿用复用优先策略：肉身层复用 M-10 已下载的 freesound CC0 预览源，背环孔膜颤动、软骨吱嘎、掌垫落点与扑跳呼啸全部由 `prepare_audio.py` 用 numpy 程序合成，无新增外部素材、无新许可负担。气炮蓄力/释放沿用既有 V06/V11 资产，不在本批重做。

## 输出（`Audio/`，48 kHz 单声道）

| 资产 | 时长 | 内容与对位 |
|---|---:|---|
| S_M08_Idle | 3.0 s 循环 | 低伏腹鸣 + 背孔膜 9 Hz 颤动 + 软骨轻吱；待机常驻 |
| S_M08_Crawl | 2.4 s 循环 | 湿掌垫交替落点 + 贴地/贴面拖行；追击、归巢与表面爬行共用 |
| S_M08_Bite | 0.95 s | 收身吱嘎 → 前探嘶吼 → 颚合（RMS 峰值 0.45 s，对位 0.85 s 动作合咬窗） |
| S_M08_Pounce | 1.30 s | 蓄力压韧 → 0.28 s 起跳呼啸 → 0.95 s 落地闷响（对齐 `PounceTravelStart=.24`/`TravelEnd=.74` 源时钟） |
| S_M08_Hit | 0.65 s | 湿肉击响 + 孔膜拍颤 + 短哼（`StaggerDuration=.55`） |
| S_M08_Death | 1.90 s | 低吟下沉 → 膜松垂 → 0.85 s 侧倒闷响 + 组织摊定（死亡 1.40 s，0.55 交接物理 ≈0.77 s 落地段） |

## 接入

- `LurkerM08Monster.h`：`M08|Audio` 6 个声音属性 + `IdleVoice`/`CrawlVoice` 组件（挂 `chest` 骨，衰减覆盖 1500/1800）。
- `LurkerM08Audio.cpp`：`UpdateM08Audio` 在 `Tick` 内轮询复制的 `EWolfState` 边沿——authority 与客户端各自本地补一次性（Bite→`head`、Pounce→`pelvis`、Stagger→`chest`、Dying→`chest`），与 M14 的 PresentState 同覆盖、不改共享犬科基类。IdleVoice 存活常驻；CrawlVoice 在存活、非攻击且实际速度 >6 cm/s 时启用（含墙面/天花板爬行）。专用服务器跳过，`EndPlay` 全部停止。
- 状态→声音：Bite/Pounce/Stagger/Dying 边沿；Howl 未接入（`bHowlOnEncounter=false`）；Ragdoll/Recovery 沿用 Dying 已播音。

## 管线

1. `python prepare_audio.py` — 生成 WAV + `Records/audio_source.json`（逐源 freesound 链接与 CC0 声明；合成层无外部权利）。
2. `finish_production.ps1` — 互斥等待 → FPSGAMEEditor/FPSGAME 构建 → `import_audio.py` commandlet 导入 `Audio/AudioV1`（Idle/Crawl 置 looping、FORCE_INLINE）→ 写 `BP_LurkerM08` CDO 六引用 → `asset_receipt.json`/`delivery.json`。

## 状态

2026-10-06 完成：双 target 构建通过、6 个 SoundWave 落盘 `/Game/Monsters/LurkerM08/Audio/AudioV1`（Idle/Crawl 循环、FORCE_INLINE），`BP_LurkerM08` CDO 写入 6 个声音引用（`asset_receipt.json`/`delivery.json`）。未做运行或验收测试，游戏内试听从用户处确认。
