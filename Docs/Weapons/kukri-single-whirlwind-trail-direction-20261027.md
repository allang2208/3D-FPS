# 单持旋风第一人称轨迹方向修正

单持第一人称使用镜头与手模的 `-2 * theta` 展示偏移，将世界身体的 `+theta` 显示为 `-theta`。`KukriSkillRift.cpp` 原先仍使用 `WhirlwindTuning.TurnDegrees` 的世界方向生成拖尾，因此尾弧位于第一人称刀身运动的前方。

`UpdateWhirlwindRiftPose` 现采用与 `GetWhirlwindCameraMotion` 相同的视角与装备条件：单持第一人称反转展示旋转量，双持或第三人称保留世界旋转量，再由展示旋转量生成后方尾弧。头部位置继续由当帧实际刀身变换提供；保留 120 度短弧、尾部渐隐和结束后的 0.12 秒消散。

改动仅在 `Source/FPSGAME/Weapons/Kukri/KukriSkillRift.cpp`，不修改动画资产、相机旋转方向、伤害扫掠或技能时钟。

源码已落盘，先通过既有 UE MCP 批次互斥执行 Live Coding，结果为 `Success / Live coding succeeded`。用户关闭编辑器后，已完成 `FPSGAMEEditor Win64 Development` 正式构建，结果 `Succeeded`，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已重新链接，后续打开编辑器使用此正式产物。

正式构建日志为 `Saved/KukriSingleWhirlwindTrailDirection20261027/editor-build-20261027-144002.log`，耗时 26.91 秒。未重新打开编辑器，未运行游戏测试，未重新打包游戏。
