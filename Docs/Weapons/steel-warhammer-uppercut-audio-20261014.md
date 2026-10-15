# 双手战锤上挑音效替换

用户指定 `D:/FPS3D/资产/音效/钝器上挑.mp3`，接入上挑武技的专属音效。

- 资产：`/Game/Weapons/SteelWarhammer20261014/UppercutAudioV1/S_Warhammer_Uppercut`。
- 制作与恢复入口：`SourceAssets/SteelWarhammer20261014/UppercutAudioV1/prepare_audio.py`、`import_audio.py`。
- 48 kHz 双声道，1.829104 秒；保留原始 MP3 及浮点解码源。只裁去 18.896 ms 开头近静音并保留 2 ms 起音预卷，尾音完整。不做均衡、变速或变调；为避免 MP3 解码峰值在 PCM 转换时削波，共用增益 0.91239142。
- SoundWave 为 PCM、ForceInline，资产音量及音高均为 1；播放音量沿用上挑原有 0.72，播放音高改为原音 1.0。
- 装备战锤时加入现有异步加载集合，发力事件使用同一个 `WarhammerAudioPaths::Uppercut` 引用，避免出手时同步读盘。
- 播放节点仍为 `WarhammerUppercutMotion::StrikeStart`（当前动作时钟 1.205 秒），每次本地上挑跨过节点时播放一次。保持现有动作时钟、伤害、命中判定与联机语义。
- 普攻、旋风、重击和冲刺砸地音效保留各自引用。
- 现有 `/Game/Weapons/SteelWarhammer20261014` cook 目录覆盖新增资产。

后台导入已保存，回执见 `UppercutAudioV1/import_receipt.json`。正式 `FPSGAMEEditor Win64 Development` 构建成功，已编译两个改动的播放／预加载文件并链接 `UnrealEditor-FPSGAME.dll`；结果由同目录 `build_receipt.json`、`build-FPSGAMEEditor.log` 记录。

未试听、未启动游戏、未运行测试，实际音画效果由用户体验。
