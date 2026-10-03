# Pit Viper 2011 用户开火声接入：首轮及提亮版记录

后续用户已将 BrightV2 指定为手枪共用消音声，2011 普通声改用 `M2011viper.mp3`。最新配方与普通／消音分支接入见 [手枪共用消音声与 2011 普通开火声](pistol-shared-suppressed-and-pit-viper-normal-20261002.md)。以下保留首轮和提亮版的制作过程。

用户指定 `D:/FPS3D/资产/音效/viper.mp3`；实际落盘文件名为 `vpier.mp3`。本轮以该文件制作并导入本枪的普通开火声，原始 MP3、浮点解码、浮点加工母版和 PCM16 WAV 均保存在 `SourceAssets/PitViper2011FireAudio20261002`，散列与具体参数见 `provenance.json`。来源按用户提供本机音频记录，不继承旧 M1911 声音的 CC0 声明。

源文件为 48 kHz 双声道、216 ms，开头存在空白及编码预卷，浮点解码峰值约 +0.54 dBFS。最初 CleanV1 采用首次超过 −50 dBFS 的样本并保留 1 ms 预卷，裁去头部 23.458 ms；尾部按 −65 dBFS 留 4 ms 余量。45 Hz 二阶高通只清理直流／次声，保留源枪声主体、机械细节、音高和声道。100 ms 窗 RMS 用于补偿轻度滤波能量，不将其称为 LUFS 或主观等响。最终双声道共用增益留出 −1.3 dBFS 峰值余量，配 0.25 ms 淡入和 12 ms 末端淡出；没有叠加合成层或重建尾音。

用户反馈 CleanV1 略沉闷后，当前已导入 BrightV2：在同一源素材上用 360 Hz／−2.5 dB／Q 0.85 钟形 EQ 减轻低中频箱体感，2800 Hz／+3.5 dB／Q 0.9 提升爆音存在感，6000 Hz／+2 dB 高架滤波提亮机械细节。滤波在连续源上完成后再沿用原裁切，保持 186.979 ms、48 kHz 双声道和音高。以 CleanV1 的 100 ms 窗 RMS 补偿能量，留 −1.3 dBFS 峰值余量后的 RMS 差为 −0.302 dB；这只是制作指标，不代表主观等响或音色验收。CleanV1 的 WAV、浮点母版、作者脚本和回执保留在 `History/CleanV1`。当前 `provenance.json` 与资产元数据记录 `BrightV2`，无需原生构建。

正式文件 `Audio/S_PitViper2011_Fire.wav` 为 186.979 ms、48 kHz 双声道 PCM16。原 `SoundWave` 的音量 1.0、音高 1.0 和声音类别保持原值，导入采用 PCM／ForceInline，保存到既有 `/Game/Weapons/PitViper2011/Integrated20261002/Audio/S_PitViper2011_Fire`。单持的 `LoadAKMSound`、双持与法杖副手的 `H.Sounds[Fire]` 继续沿用该路径，无需新增播放分支或改射击时钟；原消音分支保留。

音频资产已通过现有编辑器桥导入并保存，详见 `import_receipt.json`。导入前结束了当时已有的游玩会话以允许资产写入，没有关闭、启动或重启编辑器，没有启动新的游玩、试听或运行验收。此轮不改原生 C++，无需重编译；听感与音画效果由用户自行测试。

制作入口为 `author_audio.py`，导入入口为带批次互斥的 `run_import.ps1`。最初整枪导入和交付记录入口同步读取本次配方，以避免恢复整枪时回退到原 M1911 供体声。需要重新制作时先运行 `py -3.11 SourceAssets/PitViper2011FireAudio20261002/author_audio.py`，再执行该目录的 `run_import.ps1`；游玩中的导入会保留当前会话并暂停，结束游玩后重跑导入。
