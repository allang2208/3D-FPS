# 暗纹猎弓：CC0 音效获取与阶段接入（2026-09-26）

用户授权按推荐方案获取资源并匹配阶段导入。采用 Still North Media 的英式长弓录音，
不购买 Fab 付费包，不改变当前 ContactV9 动作或待机到 Draw 首帧的 0.2 s 过渡。

## 来源与制作

- 作者：Ben Jaszczak 与 Brian Nelson / Still North Media。
- [GitHub 来源索引与 CC0 许可](https://github.com/PanderMusubi/sound-effects-library-weapons)。仓库不是完整 WAV 库。
- [OpenGameArt 原始录音镜像](https://opengameart.org/content/medieval-sound-effects-weapon-textures)。本次取得第一包，从中提取 5 段源录音。
- [原作者使用说明存档](https://web.archive.org/web/20220331020630/https://www.stillnorthmedia.com/libraries)。
- 原始素材、许可、获取脚本、散列、制作配方与导入脚本：`SourceAssets/BowAudioStillNorth20260926/`。

英式长弓 Draw、Nock Arrow、Set Arrow、Shoot 和 Arrow Fletching 原轨均保留，
本轮从 Draw、Nock Arrow、Shoot、Arrow Fletching 裁取四个阶段片段。
Set Arrow 留在源素材中，不额外重复叠加搭箭声音。

取箭音由 Arrow Fletching 的箭羽摩擦片段制作，是动作拟音，不宣称为独立箭袋实录。
衍生 WAV 为 48 kHz、16-bit、单声道；按波形裁切、去低频、保音高适配基础时长、边缘淡化，
各片段保留峰值余量。原始 192 kHz WAV 不修改。

## 触发时序

| 阶段 | 资产 | 触发合同 |
| --- | --- | --- |
| 取箭 | S_Bow_TakeArrow（0.26 s） | R 搭箭到 28%（默认 0.1904 s）；空弦左键入场时播放，压至 0.16 s，弦上已有箭则跳过 |
| 搭箭 | S_Bow_Nock（0.16 s） | R 搭箭到 82%（默认 0.5576 s）；空弦左键到位 0.2 s 后播放 |
| 拉弓 | S_Bow_Draw（基准 1.4 s） | 进入 Drawing 当刻播放，跟随技能调整后的拉满时间；跨帧余时用于声音起始位置 |
| 放弦 | S_Bow_Release（0.473 s） | 成功生成并结算箭支时播放；取消、体力不足或发射失败不播放 |

取箭／搭箭使用单一可停止的 HandlingAudio 声部，避免摩擦压住扣弦。
拉弓使用独立 DrawAudio；满拉后停止，Holding 不循环，提前放箭、取消、收起、换装和
EndPlay 都释放相关声音。弓术缩放时播放速率会连带影响音高；未引入额外时间伸缩插件。

资产目录：`/Game/Weapons/DarkBow20260925/AudioStillNorth20260926/`。
四个 SoundWave 均非循环，ForceInline，音量／音高 1，压缩质量 100。
运行时倍率沿用拉弓 0.42、搭箭 0.5、放弦 0.6，新增取箭 0.4。

`bow_take_arrow_sound` 同步纳入异步加载与表现签名，刷新时清理旧声音引用。
`bows.json` 表现版本提升至 15，通过既有库存迁移更新旧弓；已有弓不必重新领取。
`DefaultGame.ini` 显式包含此音效目录，避免仅 JSON 引用的声音漏入打包内容。
未改弹药扣除、伤害、库存选择或动画时间合同。

## 落盘状态

- 获取：5 段原始录音及 CC0 许可已落盘。
- 制作：4 个衍生 WAV 已落盘；`audio-manifest.json` 记录精确裁切与处理。
- 导入：4 个 SoundWave 已通过无界面 commandlet 保存；回执为 `SourceAssets/BowAudioStillNorth20260926/import-receipt.json`。
- 原生构建：`FPSGAMEEditor Win64 Development` 已成功，基础模块 DLL 已链接落盘。最终日志为 `Saved/BowAudioStillNorth20260926/build-editor-final.log`。
- 源码备份：`Saved/BowAudioStillNorth20260926/Before/`，保留本轮修改前的并行开发状态。
- 未启动交互编辑器或游戏，未试听，未运行测试或音画验收，由用户测试。

首次全模块构建中弓源码编译完成，但地牢 `DungeonSpawnDirector.cpp` 与
`DungeonRoomEncounter.cpp` 的匿名命名空间常量 `MaxSlotAttempts` 在 unity 编译中重名。
为完成本轮必要构建，仅把前者的局部常量及其使用点改名为
`SpawnDirectorMaxSlotAttempts`，数值与刷怪逻辑不变；随后构建、链接成功。
原始失败日志与修改前文件都保留在上述 Saved 目录。
