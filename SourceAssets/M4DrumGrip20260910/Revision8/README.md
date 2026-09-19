# 空仓弹鼓换弹连续性修正

用户指出第 7 版插鼓后手仍悬停。回查实际游戏画面，压实（源帧 80）至拍击（116）占约 1.330462 秒；之前只消除了旧 111–125 的部分停顿，没有处理整段运行节奏。

本次只重分配空仓动作时间，沿用第 7 版已检查的手型、骨骼轨迹和引擎动画资产。压实至拍击现在为 0.450 秒：压实后迅速松握、退手、抬手、拍击。约 0.880462 秒转移至源 24–34 帧取新弹鼓阶段，该阶段现在约 1.099341 秒。总空仓时长仍 3.861572 秒；普通换弹仍 3.110374 秒。插入阶段总耗时仍为前版的 1/1.5。

空仓源时间改用单调 Hermite 曲线，所有时间节点保持精确且连接处一阶连续，不倒放或越过源帧。弹鼓脱落、出现、插入、压实和枪机释放事件通过同一 source/runtime 映射定位。慢取鼓阶段仍有渐进动作，不新增长时间完全冻结。

可编辑时序源：`Source/FPSGAME/Weapons/M4DrumReloadTiming.h`；本目录保存 `current_timing.h` 快照与 `previous_timing.h`。可编辑姿态及 FBX 继续使用 `../Revision7/M4_DrumMatch_Editable.blend`、`A_M4_DrumMatch_reload_empty.fbx`；引擎资产仍 `/Game/Weapons/M4DrumDrop/Match/A_M4_DrumMatch_reload_empty`，未重导或覆盖已验收姿态。这些源资产单独播放不包含 C++ 的非匀速时钟，应与时序头文件一起保留。

模块 `UnrealEditor-FPSGAME-2026091416.dll` 编译成功；新独立进程 `drum_flow_r8` 隔离存档、实际渲染、模拟 R 输入，报告 COMPLETE failures=0。新增测试确认压实至拍击 0.450 秒、取鼓 1.099341 秒，保留容量、弹药、独立掉鼓、普通构图和插入速度回归。`motion_flow.json` 记录源模型腕部速度检查；这个标量不用于否定用户对原版迟滞的观察，观感以实际回放为准。

`Delivery/M4_drum_reload_with_game_audio.mp4` 使用同进程 142 张截图和实际混音。7 个接触音全部播放且波形相关性至少 0.9907，无削波。30 fps 输出通过保留上一张截图填充捕获间隔，非原生 30 fps 录屏；音频只有统一时间起点，没有逐事件挪动。已查看最终插入、松手、抬手、拍击与回收接触表。

编译前置修复：`M4GunsmithPreview.cpp` 和其布局测试使用了 USceneCaptureComponent2D 不存在的 OrthoNearClipPlane/OrthoFarClipPlane。使用引擎自身的 FReversedZOrthoMatrix 表达原先的近远裁切意图，并在切到 ADS 前清除自定义投影；布局审计改从实际投影矩阵计算深度。`drum-flow-compat-1280.log` 51 项检查全过，已查看普通及 ADS 预览。保留其他并行编辑，未提交混合工作区。
