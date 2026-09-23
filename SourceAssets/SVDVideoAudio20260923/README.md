# SVD 视频音效提取 — 2026-09-23

用户指定从 [BV15MqbBcEQh](https://www.bilibili.com/video/BV15MqbBcEQh/) 的 **1:50** 开始识别并提取。视频为 127毫米发布的《三角洲音效对比 PSG-1&SR25&SVD》。依据画面中的 SVD 标注、换弹／右手拉栓动作和音轨瞬态划分事件；未进行听音复核或游戏测试。

## 提取结果

| 文件 | 原视频起止 | 用途 |
| --- | --- | --- |
| `Audio/S_SVD_Fire_01.wav` | 1:57.465–1:58.335 | 独立单发及完整衰减，避开后续连射 |
| `Audio/S_SVD_MagOut.wav` | 1:51.800–1:52.085 | 卸弹匣 |
| `Audio/S_SVD_MagInsert.wav` | 1:52.985–1:53.170 | 弹匣插入前段 |
| `Audio/S_SVD_MagSeat.wav` | 1:53.170–1:53.430 | 弹匣卡入／到位后段 |
| `Audio/S_SVD_ChargePull.wav` | 1:54.080–1:54.255 | 拉机柄后拉前段 |
| `Audio/S_SVD_ChargeRelease.wav` | 1:54.255–1:54.515 | 枪机复位后段 |

完整换弹参考保存在 `Masters/SVD_Reload_Full_01_float.wav`（1:51.400–1:54.700）和 `Masters/SVD_Reload_Full_02_float.wav`（2:01.100–2:04.550）。这些是视频混合音轨的剪辑，机械音名称按画面和瞬态推定，并非原作者提供的独立音轨标签。

## 音质与来源

- 保留下载的最高可获取音轨 `source_audio.m4a`，Bilibili 格式 30280，AAC LC 约 125.372 kbps，44.1 kHz 双声道；原视频也保留在本目录。
- `reference_110_end_float.wav` 保留 1:50 至结束的解码样本。`Masters/` 中六个 float32 WAV 是未编辑的逐采样切片。
- `Audio/` 是 UE 使用的 PCM16 WAV，保留源采样率、双声道、音高和相对音量，仅加 0.25 ms 起始／8 ms 末尾淡化。没有升采样、降噪、均衡、拉伸或伪造变体。
- 六段均未触发过载衰减，实际 gain=1。UE SoundWave 设置为 **PCM** 和 `FORCE_INLINE`，避免再次使用感知有损编码。
- **源音轨已经有损压缩，WAV/float32 不代表无损原始录音，也不能恢复 AAC 丢失的细节。**视频“现实”比较标签不构成独立实枪录音来源证明。
- 按用户提供链接作本机提取；第三方权利保留，未确立公开再分发许可，不归入此前 CC0 枪声包。未公开发布。

## 接入

六个 SoundWave 已通过后台 commandlet 导入并保存到 `/Game/Weapons/SVDDragunov20260922/VideoAudio20260923`，见 `import_receipt.json`。

`SVDWeaponAssets.h` 指向新单发音效，变体数量设为 1；视频连续射击的尾音存在重叠，因此没有切成虚假的多发独立变体。`FPSGAMECharacter.cpp` 的 SVD 分支加载五个专属机械音，普通／空仓换弹和装备拉栓沿用现有 SVD 事件时钟。其余武器、SVD 消音开火分支、装备底声、空击与暴击声保持原有来源。

本次提取和资产保存完成；构建状态见 `delivery.json`。未启动 UE 界面、PIE、试听或游戏验收，由用户测试。

## 可编辑入口

- `author_audio.py`：采样切分、边缘淡化、WAV 导出与来源清单。
- `provenance.json`：原音散列、逐段时间／采样范围及处理参数。
- `import_audio.py`：六个新声音资产导入并逐项落盘。
- `run_job.ps1`：已有编辑器走互斥桥；没有编辑器时走后台 commandlet。
- `analysis/`：为本次识别提取的源视频帧和波形图。
