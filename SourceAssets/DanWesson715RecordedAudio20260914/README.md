# 715 recorded audio authoring

用户输入：`D:/FPS3D/资产/715/715-fire.mp3`、`715-reloading.mp3`。

- `Original/`：原始文件，本机保留。用户授权本机游戏使用，再分发许可未提供。
- `process_audio.py`：浮点 MP3 解码、风噪高通与软谱衰减、八个游戏 WAV、七个接触事件及离线混音参考。
- `manifest.json`：来源 SHA-256、参数、静段降噪量、切段边界、推断阶段、主撞击及增益。
- `Cleaned/`：完整降噪录音。`Waves/`：游戏用分段。`Preview/`：离线编辑参考，未通过游戏播放链，不是实机录音。
- `Analysis/`：原录音信号分析和前后波形／接触图；decoded WAV 使用浮点格式以容纳 MP3 解码过载峰值。
- `import_assets.py`：导入八个 SoundWave 至 `/Game/Weapons/DanWesson715/RecordedAudio20260914`，Force Inline、非循环。

音频阶段归属基于瞬态顺序和现有动画推断；无源视频和本轮人工听辨。默认逐发机械音效保持原选择，七段录音只在实际安装速装器时使用。原版 6.528 秒换弹录音没有作为整段声音直接播放。

详细接触表及逻辑见 `Docs/Weapons/dan-wesson715-recorded-audio-20260914.md`。

制作与导入：八个 WAV 已制作，八个 SoundWave 已保存。`import.log` 记录 `DW715_RECORDED_AUDIO_COMPLETE count=8` 和 `Python script executed successfully`；`import-receipt.json` 保存实际资源路径。命令行进程因工程既有 GameFeatureData 资产管理配置报错返回 1，音效 Python 导入已完成。

首次导入等待共享 Build.bat 的平台 SDK 查询；只结束本任务导入进程后，采用引擎支持的 `-Multiprocess` 参数导入，避免重复平台查询。未停止其他任务的编译或用户编辑器。

原生构建：`build-native.log` / `build-native-ubt.log` 记录 `Result: Succeeded`，182 个构建动作完成，耗时 204.05 秒（包含 UBT 等待）。FPSGAME、AutoFootstep、AutoFootstepEditor 使用一致后缀 `71407`。为避免外层 Build.bat 轮询饥饿，只结束本任务尚未进入编译的批处理，改用引擎自带 DotNet 直接调用 UnrealBuildTool，保留 `-WaitMutex` 进行串行编译；没有取消其他任务。

资源导入与必要原生构建已完成。重启已打开的编辑器后加载新模块。未做 PIE、声音试听或运行测试，由用户测试；构建完成不代表实机音色或音画同步验收。
