# 螳螂 M27 — AudioV1

2026-10-07。设计名及 F6 显示名统一为 **螳螂 M27**；稳定标识 `MantisM27` 不变。

音色围绕湿润膜质、胸腔共鸣、骨质镰刃与束缚链条。隐身低而近，技能起势清楚，横劈短促有加速度。48 kHz、单声道、16-bit PCM，共 15 个 WAV。制作不包含试听、游戏测试或声学验收。

| 事件 | 设计与接入 |
| --- | --- |
| CloakEnter | 0.65 秒膜质向内吸入、链条拉紧与低频塌缩，进入隐身触发。 |
| CloakLoop | 3 秒凝胶震颤循环，短距离、低音量；退出隐身、死亡及销毁时停止。 |
| CloakExit / ShadowBreak | 0.38 秒膜质重新凝结；破影攻击版本增加爆裂和链条瞬态。 |
| SlashLeft / SlashRight | 各 0.65 秒。0.04 秒轻微蓄力链响，0.195 秒加速破风，0.258 秒空气切割峰值，0.275 秒刹停。左右音色略有区别。 |
| ScytheHitA / ScytheHitB | 0.26 秒撕裂接触，只在实际造成伤害时交替触发；挥空不包含肉体命中。 |
| PounceWindup | 0.60 秒胸腔蓄压与拉紧链条，覆盖现有飞扑准备段。 |
| PounceFlight | 0.90 秒起跳冲气和头顶下劈破风，0.54 秒强化下劈；实际落地打断尾音。没有预烘焙落地撞击。 |
| PounceLand | 0.80 秒低频落地、双镰干脆撞击与链条沉降，跟随真实 Landed 事件。即使目标闪避或格挡仍有地面接触声。 |
| Hurt / Death | 短促胸腔受击与膜质挤压；死亡使用腔体泄气和链条松脱，不预设尸体落地时间。 |
| Idle / Move | 轻微胸腔呼吸和移动膜质/链响。Move 由追逐状态及速度驱动，不冒充脚步。 |

## 实现

`MantisM27Audio.cpp` 在 BeginPlay 分配动作、转态、环境、命中共四个空间音频组件。复用已有 Tick、攻击序号、服务器动作时间及飞扑阶段，不增加伤害计时器、不在热路径加载音频或创建组件。状态延迟通过声音起播位置对齐；动作中断停止动作声。受伤声不抢占隐身/破影等正在播放的提示音。

伤害命中与真实落地使用服务端触发的非可靠表现 RPC。每次飞扑范围伤害最多触发一个肉体接触声，避免多目标叠音。M27 关闭共享飞扑特效中的突变体通用落地声，特效及其他怪物的默认声音保留。隐身约 6.5 米内的轻微声不与攻击预警使用相同传播范围。

SoundWave 保存在 `/Game/Monsters/MantisM27/AudioV1`，使用 ForceInline。`BP_MantisM27.MantisSounds` 保存强引用及角色映射，烹饪跟随蓝图依赖。导入仅更新音频映射、名称与元数据，保留现有 CombatV15、ClawV16 和 PounceV11 的动作及技能参数。

## 来源与重制

主体空气、链条非谐波、膜质共鸣及低频冲击由 `Tools/MantisM27/author_audio_v1.py` 原创合成；湿润和腔体层复用项目已有 AudioScout 记录的 CC0 预览素材：

- sillygrizzlies，Blood Gush/Squelch：[635042](https://freesound.org/s/635042/)
- federicoy，Wet Slimy Movement：[834075](https://freesound.org/s/834075/)
- SamanthaCastleberry，Stomach Growls：[695999](https://freesound.org/s/695999/)

这些输入是已有 MP3 预览文件，并非原始无损母带。原文件副本、哈希和来源保存在 `SourceAssets/MantisM27/AudioV1/Sources` 及 `audio_manifest.json`；原授权记录在 `SourceAssets/M10ChenXia20261003/AudioScout/README.md`。本次未进行新的外部下载。

后台制作入口：`author_audio_v1.py`；构建及实际导入入口：`finish_audio_v1.ps1`。后者使用项目 UE 批次互斥，构建 Editor/Game 后执行无界面 Python commandlet；不会打开编辑器或运行游戏。资产保存状态以同目录 `asset_receipt.json` 为准，编译及导入日志不代表已试听或通过游戏验收。
