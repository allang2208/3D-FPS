# 201 开火声：用户指定视频原声

来源：[QJB201轻机枪立姿射击测试原声(不掉链子版)](https://www.bilibili.com/video/BV11xwQz5EHS/)，上传者「铁烽战术」。用户指定从 25 秒后的射击提取并接入 201。

已完成：4 个 SoundWave 经后台 commandlet 导入保存，记录为 `import_commandlet.log` 和 `import_receipt.json`；代码已纳入 `Saved/BuildEditor/build-20260927-233829.log` 的成功常规构建，基础 Editor DLL 已更新。

## 制作

下载保留原始 30280 AAC 音轨；原生为 44.1 kHz 双声道。分别选取约 25.8794、26.7542、27.5860、29.8868 秒的四组连射末发，每段约 285 ms，结束于下一轮射击之前。原始解码裁切另存为 float WAV 母版。

处理包括：65 Hz 二阶高通抑制低频杂音，14.5 kHz 二阶低通收整高频；0.35 ms 起音淡入；170–285 ms 平滑收尾。前 150 ms RMS 用于匹配四段相对能量，单段匹配增益限制为 ±1.5 dB，再统一设置 −1 dBFS 样本峰值余量。RMS 是制作指标，不是 LUFS 或主观听感验收。保留音高、双声道和起音时刻，不添加合成枪声，不把整段连射作为单发播放。

输出：`Audio/S_LMG201_Fire_01.wav` 至 `04.wav`，原生采样率 PCM16。精确裁切样本、参数及 SHA-256 位于 `provenance.json`。

## 游戏接入

- 资产目录：`/Game/Weapons/LMG201/FireAudio01`。
- `LMG201WeaponAssets.h`：201 专属四变体路径。
- `FPSGAMECharacter.cpp`：普通开火单发加载和连射变体均使用 201 声库；沿用不相邻重复的选择与最多 6 声部的尾音重叠。
- 继续使用原有声音类别、播放音量倍率、开火节拍与消音分支。
- 导入脚本 `import_audio.py` 实际执行后才以 `import_receipt.json` 标记资产保存。源码编译情况另记，脚本存在不代表已经接入。

## 复现

1. 用本机 Python 的 `yt_dlp` 下载该 URL 的 `bestaudio` 至 `Source/BV11xwQz5EHS.m4a`，保留信息 JSON。
2. 运行 `author_audio.py`，使用本机 NumPy、SciPy、SoundFile、imageio_ffmpeg。
3. 当前编辑器内经 `Tools/AssetPipeline/mcp_call_codex.ps1` 执行 `import_audio.py`；没有编辑器时使用项目后台 authoring runner。
4. 常规构建更新原生播放分支，保持编辑器关闭，不自动运行游戏。

此次按用户指定 URL 在本地提取原混音；不把它描述为独立录音分轨。第三方原音频权利保留，未建立公开再分发许可；不公开提交原音轨、衍生 WAV 或 uasset。

本轮不主动试听、启动游戏或做运行验收，听感由用户测试。实际交付状态见 `DELIVERY.json`。
