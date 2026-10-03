# G18 开火声替换（2026-10-03，v3 现行）

## 三轮经过

- **v1（废案，`Work/v1_thin/`）**：Wikimedia 远场录音里选最干最亮的 4 发瞬态——>3kHz 能量占 43–88%，只有「脆裂 snap」缺枪身，用户判不合格。
- **v2（废案，git 无记录，母版已覆盖）**：同录音改选中距离混响组（中频占比对齐了）但本质还是**远场机位**——无近距枪口爆响，听感「远处炮仗+回声」，用户判**根本不像枪声**。教训：<100Hz≈0 且衰减带长回声的录音，无论怎么切/整都当不了游戏枪声主料，应直接否源。
- **v3（现行）**：**换近场 CC0 音源**——The Free Firearm Sound Library（opengameart，CC0-1.0，作者 Ben Jaszczak / Brian Nelson / Kevin Heras / Matthew Nanney）完整库 `Prepared SFX Library.7z`（194MB，sha256 cc1ab5a99a0a365105c7c5dd783f4b0b1fe90938114d3ceec53856bfe005f7d6）。选 **Walther PPQ（9mm 现代手枪，声学最贴 Glock）** 近场录音 X_39P 的三发 + @6.45s 的 1.5% 降调微变体（旧 G18 管线同款「slight variant resampling」口径）作第四发。
- **配方=复用 FirearmAudio20260913 的 M4/QBZ 已验证管线**（`prepare.py`）：起振前 1ms 切入、560ms 段、110–11000Hz 主带 + 140–650Hz 低中频补偿（0.84/0.28）、65ms 起指数衰减包络（τ=105ms）+ 末 40ms 线性淡出、24 样本淡入；**RMS 统一 0.065**（旧 G18 实测 0.063）。成品频谱 85% 中频 / 11% 低中 / 3–4% 高频，与旧 G18（84%/4%/11%）同族。

## 规格 / 导入 / 回退

- 规格：48kHz 单声道 PCM16，560ms，RMS 0.065，峰值 0.83–0.91。
- 导入：`Tools/AssetPipeline/import_g18_fire_audio_cmdlet.py`（变体）+ `import_g18_fire_base_cmdlet.py`（无后缀 S_G18_Fire=双持基础键，用 02 号母版）。交互编辑器关着走 commandlet：`UnrealEditor-Cmd -project=<绝对路径> -run=pythonscript -script=<py> -ABSLOG=<绝对路径>`。
- 五个资产已导入落盘并回读验证（23:55–23:57）。消音路（共享 S_Pistol_Suppressed）未动；C++ 零改动。
- 回退：旧官方母版在 `SourceAssets/G18Integration20260929/Audio/`，同名重导即还原。
- **未测试**：未实机听感验收，由用户进游戏试听。

## 许可

- v3 源：**CC0-1.0**（无署名义务），与旧 M4/G18 声同库同源。
- Wikimedia 那段录音（CC BY 3.0）两轮均未采用为成品，`Source/Glock18_FullAuto.ogv` 留档可删。

## 目录

- `Source/PreparedSFXLibrary.7z` + `Source/Library/` — CC0 完整枪声库
- `Source/Glock18_FullAuto.ogv`、`Work/full_audio.wav` — v1/v2 废案音源
- `Work/v1_thin/` — v1 废案四发
- `Masters/S_G18_Fire_01..04.wav` — v3 四发母版（哈希见 checksums.sha256）
- `Tools/` — ffmpeg 9.0.2 静态构建（临时工具，不入库）
