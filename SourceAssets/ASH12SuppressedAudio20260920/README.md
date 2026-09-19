# ASH-12 专属消音开火声 — 2026-09-20

用户要求：基于提供的 ASH 开火声制作消音音色，不降低音量。

## 来源与制作

- 唯一音源：`../ASH12CameraAudio20260919/S_ASH12_Fire.wav`，来自用户提供的 `D:/FPS3D/资产/音效/ash-12-fire.mp3`。
- 保留 48 kHz 双声道、0.288 秒时长和原音高；源录音及衍生声音沿用原始权利，不属于此前 Free Firearm CC0 声库。
- `author_audio.py` 使用本机 Python 3.11、NumPy、SciPy、SoundFile 制作四个细微音色变化版本。
- 圆化尖锐爆音，保留 110–520 Hz 低频主体及原声机械细节，加入从同一录音提取的约 6 / 11 ms 短腔体回声；尾部收束。
- 滤波后按源录音的全段 K 加权能量补偿响度，并要求普通 RMS 不低于原声；不用低音量模拟消音。该短声音只有 288 ms，记录的是无门限全段加权能量，不声称通过 LUFS 主观等响验收。
- 处理参数、源散列和制作时电平补偿数值记录于 `provenance.json`。没有执行试听或游戏测试。

## 接入

- `import_audio.py` 在当前 UE 编辑器导入并保存到 `/Game/Weapons/ASH12/SuppressedAudio20260920/S_ASH12_Suppressed_01..04`。
- SoundWave 的音量、音高、声音类别和压缩质量复制自现有普通 ASH 开火声；此次导入音量和音高均为 1。
- `FPSGAMECharacter.cpp` 的武器初始化仅为 ASH 选择新消音库。普通 ASH 开火声及其他枪械声库保持原引用。
- 继续使用现有四变体非连续重复选择、六声部重叠尾音及普通开火相同的运行时音量乘数。
- `DefaultGame.ini` 添加该目录的打包引用。

## 生效范围

资产已保存。C++ 本次采用现有编辑器 Live Coding，构建结果见 `livecoding-result.txt`；基础 DLL 仍须后续常规 Editor 构建纳入。已生成的补丁不等于基础 DLL 更新。
新启动 PIE 或重新装备 ASH 时会重新加载音库；本次不启动 PIE、不试听，交由用户判断声音效果。
