# 鼓囊 M-09 本体声音 V10

用户授权加入警戒、蓄压吐弹和死亡声音，由用户自行测试。使用既有 V03 动作、V08 连续软体死亡与 V09 听觉/伤害数值；不启动编辑器界面或游戏，不进行试听、自测或验收。

**2026-10-12 后续调整：用户要求去除过吵的吸气蓄力声。** 已从正式 `BP_BellowSacLobber` 的 `BellowSounds` 移除 `Charge`（`S_Bellow_Charge`），蓝图已编译并保存。下表 Charge 行仅保留为制作历史，不再播放；其他 14 个音效映射继续保留。`import_creature_audio_v10.py` 同步跳过并移除 Charge，避免重新导入恢复声音。制作脚本为 `Tools/BellowSacLobber/disable_charge_audio_v14.py`，保存回执为 `Saved/BellowMuteCharge20261012/asset-receipt.json`，修改前蓝图保存在同目录 `Before/`。本次仅修改音效绑定，无原生代码变更；结束现有 PIE 后使用原编辑器完成保存，未重开游戏或试听。

## 声音与触发

| 角色 | 时长 | 触发与位置 |
| --- | --- | --- |
| AlertA / AlertB | 0.84 / 0.92 s | 首次确认目标，在怪物位置播放；直接发现完整音量，收到群体预警为 60%；8 秒声音冷却，重复枪声刷新记忆不重播 |
| Charge | 1.20 s | 沿现有 AttackClock 从起手播放，附着 Bone_028；迟到的状态按已过去时间 seek，不随机变调；中断、失去目标、死亡或到发射点立即停 |
| SpitA / SpitB | 0.43 s | 权威端成功生成囊弹后，从实际发射点播放；阻挡取消发射时不播放；表现 RPC 丢弃超过 0.35 秒的旧事件 |
| DeathA / DeathB | 2.40 / 2.65 s | 死亡表现开始时播放一次泄压咽气，先停止存活声音；死亡阶段转换不重复播放 |
| BodyFall | 0.55 s | 软体求解器真实接地时播放一次；按撞地速度缩放，不将闷响烘焙在固定死亡时间 |

主体音量属性 `CreatureAudioGain=1.35`，发射额外乘 1.1。源 PCM 峰值留在 -4 dBFS，轻度离线饱和保留中频可辨识度；这些制作参数不代表已试听。

只分配三路可复用音频组件：喷管蓄压、本体警戒/死亡、空间接触。专服不分配。单声道空间化，警戒/蓄压最远分别约 36 / 32 米，接触声约 24 米。共享并发限制分别为警戒 4、攻击 8、死亡/落地 6，优先剔除更远的声音，声音抢占淡出 45 ms。组件销毁时停止，热路径不读盘、不临时创建声音组件。

## 软体接触衔接

共享软体组件新增可选原生接触事件，通过尸体组件转发。只有订阅者才收集表现用数据，复用既有接触点与预测速度，不增加射线，不改求解约束或物理速度。

代理点相对初始位置下落超过 10 cm，且沿地面法线的入射速度超过 65 cm/s 时发送一次接触。原地支撑的脚和微小沉降不触发。声音从对应世界接触点播放，尸体 Actor 关闭 Tick 后仍由现有软体组件推进触发。当前仅鼓囊订阅该事件。

## 来源与制作边界

| 原料 | 作者/来源 | 许可与用途 |
| --- | --- | --- |
| Monster roar | [colorsCrimsonTears / 537883](https://freesound.org/people/colorsCrimsonTears/sounds/537883/) | 页面 CC0；吸气警戒 |
| Air Burst | [JustInvoke / 138477](https://freesound.org/people/JustInvoke/sounds/138477/) | 页面 CC0；短促吐弹气流 |
| dyingBeast | [QuantumFellow / 734841](https://freesound.org/people/QuantumFellow/sounds/734841/) | 页面 CC0；死亡咽气 |
| Blood Gush and Squelch | [sillygrizzlies / 635042](https://freesound.org/people/sillygrizzlies/sounds/635042/) | 已有 M10/M27 CC0 原料；湿肉压缩与撞击 |
| stomach growls | [samanthacastleberry / 695999](https://freesound.org/s/695999/) | 已有 AudioScout CC0 记录；腹腔共鸣 |

本次外部下载为公开 HQ MP3 预览，原料副本、来源页面和散列保存在 `SourceAssets/BellowSacLobberMeshy20261012/CreatureAudioV10/Sources/`，不冒称原始无损 WAV。交付的八份 WAV 为这些原料与原创滤波气流/固定频率低频冲击混合制作的 48 kHz、16-bit、单声道 PCM。没有卡通上滑音，蓄压通过振幅和湿肉层密度变化表达。

囊弹落地到爆炸前的 S_BellowFuse 仍关闭。已有飞行、落地、爆裂声音与攻击间隔、伤害、范围、警戒规则保持当前设置。脚步、受击等不属于本次新增范围。

## 重建入口与交付记录

- `Tools/BellowSacLobber/author_creature_audio_v10.py`：保留许可来源、离线制作八段 PCM，生成 `CreatureAudioV10/audio_manifest.json`。
- `Tools/BellowSacLobber/import_creature_audio_v10.py`：在更新基础 Editor DLL 后导入 SoundWave、三份并发资源，仅修改原蓝图的声音表与声音增益，保存 `CreatureAudioV10/asset_receipt.json`。
- 目标声音目录：`/Game/Monsters/BellowSacLobber/V10/Audio`。
- 绑定蓝图：`/Game/Monsters/BellowSacLobber/BP_BellowSacLobber`，继续使用原 F6 生成入口。
- 原生实现：`BellowSacAudio.cpp`、`BellowSacLobber.h/.cpp`；首次发现接到 `MonsterAwareness.cpp`；可选落地事件接到 `M14SoftBodyDeath.*` 与 `MonsterCorpseRagdollComponent.*`。

交付状态：八份 SoundWave、三份并发资源和原蓝图已后台实际保存，`asset_receipt.json` 的 complete 为 true。导入 commandlet 日志记录 `BELLOW_CREATURE_AUDIO_V10_SAVED` 及 `Success - 0 error(s), 5 warning(s)`。

Editor 常规构建成功（14.22 s），日志：`Saved/BellowSacLobber20261012/build-creature-audio-v10-editor-r3.log`。前两轮构建修正了音频参数名与 AActor::Role 的重名问题，日志保留。Game 常规构建成功（153.13 s），日志：`Saved/BellowSacLobber20261012/build-creature-audio-v10-game.log`。未试听、未游戏测试，未启动交互编辑器。
