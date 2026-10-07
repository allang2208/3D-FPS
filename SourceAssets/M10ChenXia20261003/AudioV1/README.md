# 沉匣 M-10 音效 V1（2026-10-04）

本轮授权：沉匣全套怪物音效制作与接入。全部源素材为 CC0（免署名、可商用、可修改、可进公开仓库），来自 `../AudioScout` 已筛选的公开渠道素材；试听筛选记录见 `../AudioScout/README.md`。

## 产出与接入

`prepare_audio.py` 从 CC0 源确定性切片/变速/分层，输出 44.1 kHz 单声道 16 位 PCM 到 `Wav/`；来源与对应表在 `Records/audio_source.json`。freesound 条目目前用的是官方预览 MP3（有损）；拿到免费账号后可下原始 WAV 重跑同一脚本替换，成品引用不变。

| 资产 | 时长 | 内容 | 接入点 |
|---|---:|---|---|
| S_M10_Idle | 3.2 s 循环 | 低频腹鸣 + 沉匣腔体共鸣床，按 3.2 s 待机呼吸调制 | `BodyVoice`（躯干）存活期间常响 |
| S_M10_Crawl | 2.4 s 循环 | 湿肉足垫爬行（两条步态周期） | `CrawlVoice`，Crawl/Returning 状态 |
| S_M10_Bite | 1.6 s | 低吼起手，合咬峰值对齐 0.70 s 接触 | 进入 Bite 状态在嘴部播放 |
| S_M10_Howl | 3.0 s | 持续共鸣吼（替换原手脑嚎叫声） | `HowlVoice` 声道期播放，原衰减保留 |
| S_M10_Gas | 7.0 s | 合成带通湿嘶 + 腹腔气泡 + 低频床 | `GasVoice`（rump 插座）毒雾声道期 |
| S_M10_Hit | 0.85 s | 湿滑受击 + 52 Hz 闷击 | 进入 Stagger 在 body_front 播放 |
| S_M10_Death | 2.5 s | 下行咽气 + 约 1.45 s 湿重塌落（对位 60% 物理交接） | 进入 Dying 播放 |
| S_M10_Threat | 2.4 s | 攻击威慑吼 | `ThreatSerial` 复制触发，冷却 18 s |

## 代码改动

- `M10Mawcrawler.h/.cpp`：`M10|Audio` 七个 `EditDefaultsOnly` 声音属性 + `ThreatCooldown`；`BodyVoice`/`CrawlVoice`/`GasVoice` 组件；`UpdateLoopAudio()` 按状态启停两条循环；`PresentState` 状态驱动一次性音效（各客户端经复制状态播放，跳过专用服务器）；`ThreatSerial` 复制 + `OnRep_Threat`，`StartAttack` 在冷却允许时递增并本地呈现。
- `M10RearGas.cpp`：`UpdateGasPresentation` 镜像嚎叫表现，声道起点播放/结束停止，`StopRearGas` 同步停声。
- 衰减：循环组件 1100–1600 cm；一次性音效走 `PlaySoundAtLocation` 带运行时 USoundAttenuation。

## 制作与导入

- `import_audio.py`：commandlet 导入 `Wav/` → `/Game/Monsters/M10Mawcrawler/Audio/AudioV1`，Idle/Crawl 置 looping、全部 FORCE_INLINE；把 7 个声音 + `howl_sound` 替换为 S_M10_Howl + `threat_cooldown=18` 写入 `BP_M10Mawcrawler` CDO；元数据标签 `M10.AudioRevision=M10AudioV1_20261004`；`asset_receipt.json` 记录实际保存。
- `finish_production.ps1`：沿用既有批次互斥（等编辑器/构建空闲 → Editor/Game 构建 → mutex 内 commandlet）。构建与保存回执见 `delivery.json`。

## 状态

2026-10-04 已通过 `finish_production.ps1` 完成 FPSGAMEEditor/FPSGAME 双构建（均 Succeeded）与 commandlet 导入：8 个 SoundWave 保存至 `Content/Monsters/M10Mawcrawler/Audio/AudioV1/`，`BP_M10Mawcrawler` CDO 已写入 7 个声音引用 + `ThreatCooldown=18` 并保存。回执：`asset_receipt.json` / `delivery.json`，构建与导入日志在目录根部。未做运行或验收测试——游戏内试听从用户处确认。
