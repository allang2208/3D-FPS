# 用户提供的撞门音效（2026-10-02）

用户指定源文件：`D:/FPS3D/资产/音效/撞门.mp3`。`Original.mp3` 为原文件本机留存，`S_DoorPushImpact.wav` 为供 UE 导入的 48 kHz、16-bit PCM WAV；保留完整录音和原声道，不裁剪、不归一化。

目标为现有 `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact.S_DoorPushImpact`。复用原触发逻辑、0.36 s 接触事件和 0.85 播放音量倍率，保留现有 SoundWave 设置。来源记录为用户提供的本地音频，不继承旧候选的 CC0 授权声明。

制作由 `prepare_audio.ps1` 完成；接入由 `import_audio.py` 完成。实际导入和保存状态以 `import-receipt.json` 为准，导入前资产保存在 `BeforeAsset/`。当前 UE 已打开时通过现有批次互斥 Python 桥执行；运行 PIE 时等待用户停止后再替换。

未试听、未运行游戏测试。旧外网候选源和处理记录已归档到 `trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/Audio20261002/`，仅供历史恢复。
