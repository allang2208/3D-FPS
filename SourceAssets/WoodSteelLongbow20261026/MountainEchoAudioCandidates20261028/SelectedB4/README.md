# 山鸣弓弦：B4 能量冲击音效接入

用户在 B4 试听后于 2026-10-28 指定“接入游戏”。接入 `EnergyFusionV4/B4_GoldenArrow_EnergyImpact.wav` 的单次版本，保留 1.02 秒、48 kHz 双声道以及原音量、音高；不使用连播两次的试听文件。

声音资产：`/Game/Weapons/WoodSteelLongbow20261026/MountainEchoAudioB4/S_MountainEcho_EnergyImpact`。制作原料、加工及署名位于上级 `EnergyFusionV4`；本目录保存已选源副本、导入脚本和回执。

弦影箭在敌人、训练靶和障碍物命中处，与原有金色爆裂使用同一复制的命中位置。各渲染端仅播放一次；声音与粒子分别记录完成状态，避免异步加载顺序造成漏播或重播。装备弓弦时预加载，箭实例也沿现有异步请求包含此声音；不增加热路径同步加载或 RPC。

SoundWave 使用 PCM / ForceInline、音量 1、音高 1、非循环。附带 3D 衰减：中心半径 4 m，向外衰减 70 m；共享并发上限 8 声部，超限优先停止最远、再停止最旧，退出淡出 30 ms。播放不报告 AI 听觉刺激，维持弓箭原有警戒规则。

已有 `/Game/Weapons/WoodSteelLongbow20261026` Cook 配置覆盖本资产。署名随已有 `ColdSteelData/Licenses` 打包规则携带。

本轮不改变普通箭、穿心箭释放声、弓弦层数、伤害或弹道。资产保存与构建状态见 `import-receipt.json` 和 `build-*.json`；不自动运行游戏、试听或联机验收。

2026-10-28 交付状态：SoundWave、SoundAttenuation、SoundConcurrency 已通过后台 commandlet 导入并保存；FPSGAMEEditor 与 FPSGAME Win64 Development 构建均成功。未启动游戏，未进行游戏内试听或联机测试，由用户测试。
