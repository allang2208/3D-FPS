# 手枪共用消音声与 2011 普通开火声

用户指定将此前的 BrightV2 作为所有支持消音器的手枪开火声，并用 `D:/FPS3D/资产/音效/M2011viper.mp3` 处理后替换 2011 普通开火声。当前支持范围为 M1911、G18、Pit Viper 2011，包含单持、双持和法杖副手。

共用消音文件 `Audio/S_Pistol_Suppressed.wav` 直接保存用户选定 BrightV2 的 PCM16 数据，不再次改变音色、音高或时长。48 kHz 双声道、186.979 ms，原始用户源为 `vpier.mp3`。独立资产为 `/Game/Weapons/PistolSharedAudio20261002/S_Pistol_Suppressed`；选择来源、散列及支持范围记在 `suppressed_provenance.json`。原 BrightV2 的母版、作者脚本与回执另保存在 `History/BrightV2`。

新普通声源 `M2011viper.mp3` 为 48 kHz 双声道、1.032 s。作者脚本裁去 19.896 ms 编码预卷，保留 1 ms 起音余量；沿用 45 Hz 次声清理，采用 400 Hz／−1.5 dB 钟形、3000 Hz／+1.8 dB 钟形与 6000 Hz／+1 dB 高架 EQ。前 220 ms 保留原主体和早期尾响，随后逐步收尾到 620 ms，避免一秒长尾随连续射击一直叠加。0.25 ms 淡入与末端 12 ms 淡出保持无点击边缘，音高与双声道保留。

该普通声以之前 BrightV2 的前 100 ms RMS 作制作补偿，最终该窗能量相同；−1.3 dBFS 为上限，实际样本峰值约 −7.694 dBFS，没有为凑峰值额外增大已经匹配的能量。这个指标不是 LUFS，也不是主观等响。正式 WAV 为 620 ms PCM16，普通声音资产仍是 `/Game/Weapons/PitViper2011/Integrated20261002/Audio/S_PitViper2011_Fire`；来源、配方与版本 `M2011NormalV3` 见 `provenance.json`。原始 MP3、浮点解码和浮点母版均保留，不沿用旧供体的许可声明。

普通声沿原 Fire 路径加载。共用消音声在 `PistolAudioAssets.h` 定义一次：装备时 M1911／2011 显式绑定，G18 单持消音数组只加载这一个共用单发；消音器装配刷新也绑定同一资产。双持与法杖副手复制各自装配角色的消音绑定，G18 的随机四变体仅用于普通开火，避免消音声被旧变体覆盖。射击时钟、音高、音量乘数和声部合同继续沿用原实现。共用音源已加入 `DefaultGame.ini` 的 cook 根目录。

源和脚本集中在 `SourceAssets/PitViper2011FireAudio20261002`。`author_audio.py` 制作新普通声；`import_audio.py` 保存普通声后调用 `import_suppressed.py` 保存共用消音声；`record_delivery.py` 同步整枪的源记录。原整枪恢复入口执行这一套，后续不会把普通声还原成 BrightV2，也不会把消音声还原成原步枪供体。需要编辑器退出后完成整批时，使用 `run_background_install.ps1`，它等待现有编辑器退出，再依次后台导入和正式构建，不关闭或启动编辑器。

两份 SoundWave 已通过后台 commandlet 导入并保存，分别记录在 `import_receipt.json`、`suppressed_import_receipt.json`。正式构建结果为 `Succeeded`，原生 DLL 已落盘，见 `build_receipt.json`。此轮未试听、未启动游戏、未进行运行验收，听感和两条分支由用户自行测试。
