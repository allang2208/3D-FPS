# 启动主界面与资源预加载

2026-09-24，用户反馈装备与墙面纹理不清晰后，新增两档进入方式。主界面嵌入当前地图的首次本地玩家入口，以不透明页面覆盖画面并暂停世界；没有新增或替换基地地图，也没有改动角色存档。PIE 和独立运行在开始控制角色前均显示选择。

## 两档行为

| 方式 | 准备范围 | 纹理预算 |
| --- | --- | --- |
| 快速测试 | 原有场景生成、碰撞、导航准备；随后逐步流送高清纹理 | 继承本次会话原始纹理池设置，当前配置为 RHI 可用图形内存的 30% |
| 完整预加载 | 原有准备结束后，继续等待当前世界组件所用材质、纹理、异步资源与渲染管线；完成后释放玩家 | 按 RHI 报告的可用图形内存取 45%，保留其余空间用于几何、光照及渲染目标 |

选择记录在 `Saved/Config/WindowsEditor/GameUserSettings.ini`（独立游戏使用对应平台配置目录）的 `[FPSGAME.Loading] Mode`：0 快速、1 完整。主界面仍每次启动显示，上次选择获得默认焦点；一次游戏内切换基地、丘陵和地牢沿用本次选择。

保留光追、Lumen、原有画质及 `r.Streaming.LimitPoolSizeToVRAM`。不关闭纹理流送、不设无限预算、不修改纹理文件分辨率。退出 PIE / GameInstance 时恢复本会话修改的池值；若用户已手动改变该值，不覆盖新值。

## 完整档的完成条件

准备器分帧收集当前世界已注册、可显示组件使用的材质，包含第一人称装备、角色身体、实例化房间与环境组件；隐藏但参与隐藏阴影的组件仍纳入。角色为切枪预建的隐藏且不投影武器组件不算当前装备，避免把所有枪型同时强制载入高清纹理。同一材质和纹理去重。主线程工作按约 2ms 阶段预算推进，不使用等待式 FlushRenderingCommands 或阻塞流送。

- 材质必须具有可渲染 shader map；编辑器中明确的编译错误会停止准备，并显示材质名称。
- 普通 2D 纹理等待当前质量允许、已安装的非 optional mip；不使用可能永远不满足的 `IsFullyStreamedIn()` 作为唯一条件。
- 按纹理总需求先估算预算，超过纹理池 85% 时保留加载页面并说明所需容量，不以降低清晰度冒充完整成功。
- 通过引擎的流出保护接口保留本次准备集，异步 StreamIn 请求高清 mip；地图切换、取消或退出时释放。保护仅覆盖本次场景使用集，不覆盖整个 Content。
- 等待当前异步加载、组件编译、子关卡流送、实际 PSO 任务完成。稳定一段时间后再次收集，覆盖延迟装配的装备和新组件，最后等待非阻塞渲染围栏。

总资源准备时限 120 秒。超时显示当前等待项，提供「重试资源准备」及「返回主界面」重新选档；不自动降为快速档、不自动释放玩家。原有地图生成失败仍使用原来的取消／返回基地路径。完整档附加等待期间暂停玩家移动并临时关闭受伤，完成／取消恢复原状态。

完整档针对当前已加载／生成场景，不承诺提前加载尚未生成的整个开放世界、未来新装备或整个资源仓库。虚拟纹理仍由引擎按可见页请求；该流程不把所有 VT 页永久装入显存。加载设置也不能修复丢失的源资产或错误 shader；发现可判定的失败时明确停留，而非宣称成功。

## 制作范围与入口

- `Source/FPSGAME/UI/TransitLoadingSubsystem.*`：主界面、模式保存、纹理池策略、输入／暂停／玩家保护与加载界面。
- `Source/FPSGAME/UI/GameResourcePreparation.*`：当前世界资源收集、异步 mip 请求、就绪与失败状态、驻留保护释放。
- `Source/FPSGAME/FPSGAMEPlayerController.cpp`：HUD 初始化之后展示启动主界面。
- [UI 规划](../UI/startup-loading-modes-plan-20260924.md)。

开发命令行可显式使用 `-GameLoadingMode=Quick` 或 `-GameLoadingMode=Complete` 选择并跳过菜单；`-SkipStartupMenu` 保留快速直入方式。没有自动触发任何测试或脚本。

最终增量构建均已完成，包含最后的隐藏武器收集范围调整：

- `FPSGAME Win64 Development`：成功，产物 `Binaries/Win64/FPSGAME.exe`；日志 `Saved/Logs/StartupLoading-Game-20260924-03-console.txt`。
- `FPSGAMEEditor Win64 Development`：成功，产物 `Binaries/Win64/UnrealEditor-FPSGAME.dll`；日志 `Saved/Logs/StartupLoading-Editor-20260924-03-console.txt`。

用户已授权保存并关闭编辑器。交互编辑器在桥接关闭请求送达前已正常退出，因此本轮桥接未执行保存操作；随后等待已有后台 commandlet 退出，完成 DLL 链接，没有重新打开编辑器。

未启动游戏、PIE、截图、性能采样或验收，由用户自行测试实际外观和加载体验。

## 初始界面没有鼠标（2026-09-25 修复）

用户反馈启动主界面看不到鼠标指针。菜单自身逻辑是对的：`ShowStartupMenu` 设 `bShowMouseCursor=true` 并 `SetInputMode(FInputModeUIOnly())`；`FInputModeUIOnly::ApplyInputMode`（`PlayerController.cpp:6372`）随后把视口设为 `NoCapture` + `SetIgnoreInput(true)`，所以既不会因捕获隐藏光标，第 352 行那句 `VP->SetIgnoreInput(true)` 也只是与它重复（拆除时按 `bStartupPreviousIgnore` 还原，不改变结论）。

真正原因是执行顺序：`ShowStartupMenu` 在 `AFPSGAMEPlayerController::BeginPlay` 末尾调用，而 `AFPSGAMECharacter::BeginPlay` 晚于它，末尾无条件执行 `PC->SetShowMouseCursor(false)` + `SetInputMode(FInputModeGameOnly())` 来恢复第一人称默认，把菜单刚设好的光标和输入模式抢了回去。引擎日志逐条对应：`04:26:22` `MouseLockMode LockOnCapture -> DoNotLock`（菜单生效）→ `04:26:25` `Player bShowMouseCursor Changed, True -> False` 且 `DoNotLock -> LockOnCapture`（Pawn 抢占）。全日志只有这一次 `True -> False`，故启动路径上抢占者唯一；背包、枪匠、强化、体素面板等 `SetInputMode(FInputModeGameOnly())` 都由面板开关驱动，不参与启动。

修复三处：

- `UTransitLoadingSubsystem::OwnsPlayerCursor()`：主界面或加载遮罩当前是否持有光标（只读 `StartupOverlay` / `Overlay` + `CursorController`，不新增状态）。头文件补 `class SWidget;` 前置声明，使该头不依赖包含顺序。
- `AFPSGAMECharacter::BeginPlay`：`OwnsPlayerCursor()` 为真时跳过恢复第一人称默认。菜单与遮罩拆除时都会自行还原 `GameOnly` + 隐藏光标，因此跳过不留残余状态；若顺序反过来（Pawn 先、菜单后），菜单仍会在最后覆盖，两种顺序都成立。
- 加载遮罩的 Tick：原来只在 `CursorController != PC` 时夺回光标，被后来者清掉后不会恢复；补 `else if(!PC->bShowMouseCursor)PC->bShowMouseCursor=true;`，遮罩存续期间每帧夺回。地图旅行中新 Pawn 的 `BeginPlay` 同样会晚于遮罩，这条覆盖那一类时序。

按用户选择等待其关闭编辑器后再构建，本轮未编译、未运行，实际指针表现待用户自测。
