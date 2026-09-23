# PKM 后拉／前推的参考原声音效 35

2026-09-23。用户已保存并关闭编辑器，要求补齐 Charge34 常规构建，并从指定视频重新截取音效接入。

## 声音制作和时点

直接解码本机原视频 `../References/PKM_UserReloadReference.mp4`，来源为用户指定的 BV1jHeA6sEmj。使用视频成品混音中的原声片段；不是独立音效分轨，也不是合成或其它枪械录音。来源和衍生文件的许可记录随 `audio_manifest.json` 保留，仅本机使用，不新增再分发授权。

| 事件 | 视频截取范围（秒） | 空仓动画触发（秒） | 文件时长（秒） |
| --- | --- | --- | --- |
| 后拉摩擦 ChargePullMove | 24.180–24.710 | 5.13 | 0.230 |
| 后止点 ChargeRearStop | 24.710–24.905 | 5.36 | 0.192 |
| 前推摩擦 ChargePushMove | 24.905–25.010 | 5.48 | 0.340 |
| 前止点 ChargeFrontStop | 25.010–25.225 | 5.82 | 0.212 |

移动片段使用保持音高的时间伸缩，填入各自的滑动区间；金属止点保留原速并裁去起音前沿的弱信号，不随摩擦声一起拉长。80 Hz 高通、剪辑边缘淡入淡出、48 kHz 单声道 PCM16；四段使用同一增益，以最强片段 -4 dBFS 为余量，保留片段之间的相对力度。原始视频的环境底声仍可能存在。SoundWave 沿用现有 PKM 声音类别与音量设置，pitch 为 1，FORCE_INLINE 加载。

## 接入

- 音频放入独立 `/Game/Weapons/PKMLowpoly20260922/ChargeAudio35/`，保留旧 ReloadAudio22 资产及普通换弹声音。
- PKM 空仓机械事件由原先两个拉栓点改成四个，事件与镜头共同读取 5.13／5.36／5.48／5.82 秒源时钟；最后到位事件索引改为 8。
- 镜头分别读取后拉、后止、前推、前止四个时点，与 Charge34 手臂和拉柄一致。声音是分段事件播放，换弹速度变化时止点仍按当前动画时钟触发。
- 五个 Charge34 空仓动画此前已正式导入保存，本轮不重复导入。装备、普通换弹、其它枪械、弹药结算和 6.6 秒基础空仓时长保持。

`author_audio.py` 为视频裁切与处理入口；`audio_manifest.json` 记录来源散列、片段范围与动作时点；`import_audio.py` 为后台资产导入入口。

## 执行状态

四段 WAV 已制作，后台 Python commandlet 已导入并保存四个独立 SoundWave，退出码 0；`import_receipt.json` 记录资产、时长和音量，日志为 `import_background.log` / `import_console.log`。

首次常规 Editor 构建日志 `build_editor.log`：冶炼界面的缺失类型 include、错误的 `Kismet/ImageUtils.h` 路径和私有 `FDateTime::Ticks` 访问阻断构建。仅作必要兼容修正：`ColdSteelHUDWidget.cpp` / `ColdSteelWarehouseHUD.cpp` 补齐类型头文件，`ColdSteelSmeltingWidget.cpp` 改用 `ImageUtils.h`，`SmeltingSystem.cpp` 改用 `GetTicks()`，保留其它制作内容。

第二次构建 `build_editor_final.log` 仍失败，涉及冶炼 UI 的数组语法、按钮动态事件／UI API，以及 `FVoxelSmeltingJob` 缺少 `StartTicks` 的接口变化。其后该部分源码更新，本任务未继续改写该功能。中间一次 `build_editor_completed.log` 仍有颜色与 UImage API 错误；源码再次更新后，最后执行常规构建，自动等待已有 Build.bat 结束，返回 `Target is up to date`、`Result: Succeeded`，退出码 0，日志为 `build_editor_delivered.log` / `build_console_delivered.log`。

最终交付：四个 SoundWave 与五个空仓动画均已保存，PKM 四事件声音与镜头时点的源码已落盘，常规 FPSGAMEEditor 目标构建成功。本条替代中间失败状态；构建成功不表示已做游戏内音画或手感验收。

未启动交互编辑器，未运行游戏测试或试听验收。
