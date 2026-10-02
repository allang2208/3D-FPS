# 撞门音效候选（2026-10-02）

上一轮仅读取素材作者页面、文件信息与官方授权，没有下载、试听或导入，因此当时游戏没有撞门声音。下表保留原候选记录，内容适配依据作者说明，未作实际听感评价。

## 用户指定音效替换（当前，2026-10-02）

撞门声音已替换为用户提供的 `D:/FPS3D/资产/音效/撞门.mp3`。完整转换为 0.672000 s、48 kHz、16-bit PCM、2 声道 WAV，保留录音长度和原声道，不裁剪、不归一化。来源按用户提供记录，不继承旧候选的 CC0 声明。

同一个 SoundWave `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact` 已通过现有编辑器 Python 连接导入并保存；保留原音量、音高、加载方式及音频分类。运行逻辑仍为成功开门后的 0.36 s 事件播放一次，音量倍率 0.85，独立于镜头抖动设置。制作源、旧资产备份和本次回执位于 `SourceAssets/DoorPush20261002/UserAudio20261002/`；导入输出为 `Saved/DoorPushUserAudio20261002/import-live-editor-02.txt`。本次只替换资产，不需要原生编译；未试听、未运行游戏测试。

## 已替换的旧音效来源

采用 [Kodack 的 Punching a Door](https://freesound.org/people/Kodack/sounds/256857/)，素材页标明 [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。实际取得的是原作者页公开提供的高质量 MP3 预览，未下载需要登录的原始 WAV；下载地址、页面与授权快照保存在 `trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/Audio20261002/provenance.json` 及同目录。

已裁出源录音 0.459–1.105 s 的单次撞击和衰减，移除起始等待，冲击起点距输出开头约 1 ms。输出为 0.646 s、48 kHz、16-bit PCM 单声道 `S_DoorPushImpact.wav`，处理短首尾渐变、直流偏移与峰值余量。制作脚本和保存参数见同目录 `author_audio.py`、`production-receipt.json`。

SoundWave `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact` 已在本轮实际导入保存，回执位于 `trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/Audio20261002/import-receipt.json`，导入日志位于 `Saved/DoorPushGuardOnlyV5_20261002/audio-import.log`。运行源已加入 BeginPlay 异步预载，成功打开原目标门时在当前 0.36 s 护拳保持结束点播放一次，音量倍率 0.85；独立于镜头抖动开关。已加入打包目录清单，未试听或运行游戏。

## 原候选记录

| 候选 | 作者与内容说明 | 文件信息 | 授权与下载 |
| --- | --- | --- | --- |
| [Punching a Door](https://freesound.org/people/Kodack/sounds/256857/) | Kodack；作者说明是真实拳击木门录音。优先作为左拳接触的撞击候选。 | WAV，1.813 s，44.1 kHz，16-bit，立体声 | 素材页标明 CC0；Freesound 下载需登录。 |
| [door hit #2](https://freesound.org/people/ssierra1202/sounds/391964/) | ssierra1202；作者说明是拍击木门。可作较轻木门的备选。 | WAV，0.858 s，44.1 kHz，16-bit，立体声 | 素材页标明 CC0；Freesound 下载需登录。 |
| [Banging On Door](https://pixabay.com/sound-effects/film-special-effects-banging-on-door-192163/) | Universfield；页面标签包含木门、重敲、撞击。作为撞门候选，需试听后选取单次冲击。 | MP3，页面显示 2 s | Pixabay Content License；页面提供试听与下载入口。 |
| [Door open, door close](https://opengameart.org/content/door-open-door-close) | Iwan Gabovitch / qubodup；9 个真实房门开关文件。适合作为接触后的门叶运动辅助层。 | door.7z，约 1.9 MB | 素材页标明 CC0，页面直接提供下载。 |

另有标注 Kodack (Freesound)、同名的 [Pixabay Punching a Door 试听页面](https://pixabay.com/sound-effects/household-punching-a-door-104298/)，提供 MP3。该入口标示 Pixabay Content License；未确认其音频字节与 Freesound WAV 一致，本轮未从该入口取文件。

[CC0 官方说明](https://creativecommons.org/publicdomain/zero/1.0/)允许复制、修改及商业使用，无需取得许可或强制署名。[Pixabay 授权摘要](https://pixabay.com/service/license-summary/)及[服务条款](https://pixabay.com/service/terms/)允许免费使用、修改及商用、无需署名，但禁止把原始素材独立转售或再分发。

旧版采用原作者公开预览中的单次撞击，对齐当前动作 0.36 s 事件点（举拳 0.06 s、完整保持 0.30 s 后直接恢复）。未叠加门叶运动声音；听感交由用户在游戏中测试。
