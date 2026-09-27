# 打铁音效来源

用户于 2026-09-27 指定使用本机 `D:/FPS3D/资产/音效/打铁.mp3`。项目内原录音副本为 `ForgeHammerImpact.mp3`，未修改外部原文件；原合成 WAV 已归档至 `trash/forging-publication-20260927/SourceAssets/ForgeInteraction20260927/AudioSource/ForgeHammerImpact-synthetic-before-user.wav`。

`Tools/Forging/author_sound.py` 优先将此 MP3 转换为上级目录的 `ForgeHammerImpact.wav`（48 kHz、单声道、16 位 PCM），保留录音时长，不裁切、不做响度归一化。全套锻造资产重新导入时也沿用该 WAV。

`Tools/Forging/import_forge_audio.py` 仅替换并保存 `/Game/Props/ForgeInteraction20260927/SW_ForgeHammerImpact`。运行逻辑继续在锤面接触时播放，保留已有命中／偏击音量与音高设置，关闭音频循环。未运行游戏或试听验收，具体保存结果见上级目录 `audio-import-*.json`。

录音由用户提供用于本项目；此记录不推定对外再分发许可。
