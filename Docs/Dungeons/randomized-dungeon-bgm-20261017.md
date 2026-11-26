# 随机地牢 BGM 迁移（2026-10-17）

用户要求：从 E 盘原 gamedev 项目迁入恶魔地牢 BGM。

## 原曲来源

- 项目：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。
- `data/dungeon-config.json` 将恶魔洞窟登记为 `demonCavern`；`src/ui/expedition-system.js` 的地牢出征使用 `scene7`。
- `src/ui/sound-manager.js::playBgmForScene` 优先取 `dungeonBgm[dungeonType]`，缺省回退 `bgm.scene7`。
- `data/audio-config.json` 没有 `demonCavern` 专用覆盖，因此实际音轨为 `assets/sounds/music/dungeon_echo.mp3`；音乐声道音量 `0.6`、淡入 `1.5` 秒。
- 原文件和当时音频配置保存在 `SourceAssets/DungeonBGM20261017/Original/`，来源、SHA256 和导入配方见同目录上一级的 `provenance.json`。

## 接入

- SoundWave：`/Game/Audio/DungeonBGM20261017/S_DungeonEcho`。
- 全曲 199.248 秒，48 kHz 双声道；解码为 PCM24 导入，不裁剪、不均衡、不移调、不调整原曲电平。
- 资产开启循环，BinkAudio 压缩质量 80、Music 音频组、PrimeOnLoad 流式缓存；音量为零时允许继续虚拟播放。
- `FPSGAMEPlayerController::BeginPlay` 在 `L_Dungeon_Randomized` 的本地玩家端建立非空间音频组件，异步加载音轨后以 1.5 秒淡入。
- 复用既有 `HubMusic` 组件字段和 `SetHubMusicUserVolume` 入口，保留存档键 `ColdSteel.GameMenu/HubMusicVolume`，菜单文字改为“背景音乐”。默认播放音量为 `0.6 × 用户设置`，总音量继续由现有音频设备设置控制。
- 组件随玩家控制器／地图销毁停止；异步回调忽略已经退出或换图的控制器。不新增 Tick、计时器或音频网络 RPC。
- `DefaultGame.ini` 显式加入音轨目录，确保打包时包含软引用资源。

## 交付状态

资产已由后台 commandlet 导入并保存，退出码 0；`SourceAssets/DungeonBGM20261017/import-receipt.json` 记录 `saved=true`。导入日志为 `Saved/DungeonBGM20261017/import-commandlet-01.log`。
导入时现有编辑器处于 PIE，因此没有在其中导入或中断游戏；后台仅新建本批独立音轨包，没有覆盖其已加载资产。

2026-10-18 构建完成：

- `FPSGAME Win64 Development`：成功（退出码 0，6.90 秒，现有目标已是最新），日志 `Saved/DungeonBGM20261017/game-build-02.log`。
- `FPSGAMEEditor Win64 Development`：常规构建成功（退出码 0，12.86 秒），基础 `UnrealEditor-FPSGAME.dll` 已链接落盘；日志 `Saved/DungeonBGM20261017/editor-build-01.log`。构建时编辑器已关闭，本任务没有关闭或重启编辑器。
- 先前训练靶／锤动作源文件的编译冲突已在共享工作区修正后重新构建；本任务没有修改这些文件。
未启动游戏、未试听、未执行运行测试，实际听感和换图效果由用户测试。
