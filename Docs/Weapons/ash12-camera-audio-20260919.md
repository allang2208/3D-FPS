# ASH-12 换弹镜头与用户开火声（2026-09-19）

## 用户反馈与参考

用户接受换弹动作方向，反馈换弹镜头歪斜，要求按原视频优化镜头抖动，并用 `D:/FPS3D/资产/音效/ash-12-fire.mp3` 替换本枪开火声。

参考仍为 `Saved/Ash12ReloadRef/ref.mp4`。本轮读取 6.40 / 6.80 / 7.43 / 7.77 / 8.20 / 8.40 秒全画面，观察背景与枪身的相对运动：换匣时枪体侧转，背景没有同等幅度的持续侧滚；右手从上方拉栓时视线抬起，释放后回落。普通换弹沿用换匣段，不追加空仓抬头段。这是基于二维参考的手工镜头编排，并非提取到原游戏相机轨道。

参考资料：[reference-camera.jpg](../../SourceAssets/ASH12CameraAudio20260919/reference-camera.jpg)。已按项目入口调用 DeepSeek 读图，返回的是未完成的分析文本，仅留档，不作为定量依据；本轮同时实际查看参考抽帧。没有渲染或启动新动作验收。

## 镜头修改

实现位置：`Source/FPSGAME/Weapons/WeaponActionCameraComponent.cpp` 的 ASH-12 分支。

- 旧镜头键含持续 `-4.6°` 至 `-6.6°` 的 Roll，之后还会经过全局 Strength、FollowStrength 和角色 CameraMotionScale。它把枪体展示侧滚传到了整个画面，是这次持续歪斜的来源。
- 新版将 ASH-12 换弹跟随与接触冲击的 **Roll 均置零**。枪身和双臂的动画侧转继续使用上轮动作。
- 换匣阶段镜头保持平稳，接触时主要通过俯仰与少量前后、上下位移体现重量。
- 脱匣回弹 0.34 秒；入井 0.20 秒；压实 0.32 秒。入井脉冲在压实前结束，压实也在后拉前恢复，取消旧版几个大幅波形长时间重叠的漂移感。
- 空仓右手接近拉机柄时抬头，后拉阶段维持重心，2.60 秒释放后产生 0.34 秒回弹并收稳。普通换弹压实后直接恢复。
- 继续使用动作源时间和当前 0.36 / 1.56 / 1.86 / 2.34 / 2.60 秒接触点，速度属性仍同时缩放动作、镜头与机械音效。
- 调整仅在 ASH-12 镜头分支；共享镜头强度配置不变。

## 开火音效

- 来源：用户指定本机文件 `D:/FPS3D/资产/音效/ash-12-fire.mp3`。本轮用于该工程，不据此推定公开再分发许可。
- 转换入口：[prepare_sources.py](../../SourceAssets/ASH12CameraAudio20260919/prepare_sources.py)。保留原有 48 kHz 双声道，解码为 16-bit PCM WAV；不变调、不拉伸、不做响度归一。
- WAV：[S_ASH12_Fire.wav](../../SourceAssets/ASH12CameraAudio20260919/S_ASH12_Fire.wav)，解码时长 0.288 秒。
- 导入入口：[import_audio.py](../../SourceAssets/ASH12CameraAudio20260919/import_audio.py)。资产 `/Game/Weapons/ASH12/Audio20260919/S_ASH12_Fire`，单发、不循环、ForceInline 加载。
- `ASH12WeaponAssets::FireSoundPath` 与 `LoadAKMSound` 指向新声；ASH-12 普通开火变体数组只装入这一条音效，避免初始化阶段被共享 M4 数组覆盖。
- 连射复用现有最多 6 声部的播放器，尾音可与下一发重叠，保持原音高。消音器继续使用既有独立消音分支。

## 交付状态

已完成镜头与声音引用代码、参考读取、WAV 转换及 UE 音频导入。导入进程退出码 0，日志记录 `ASH12_FIRE_IMPORT_COMPLETE`，资产保存在本枪独立 Audio20260919 目录；记录见 [import.json](../../SourceAssets/ASH12CameraAudio20260919/import.json)。

用户保存并关闭编辑器后，已用 `Tools/Build/Build-Editor.ps1` 完成普通 Editor 原生构建：9 个构建动作，重新编译镜头组件并链接 `UnrealEditor-FPSGAME.dll`，结果 `Succeeded`。日志：[build-20260919-174754.log](../../Saved/BuildEditor/build-20260919-174754.log)。重新打开工程即可加载本轮镜头和新开火声引用。

按用户规则，未进行实机、试听回归、截图或自动测试，手感由用户测试。
