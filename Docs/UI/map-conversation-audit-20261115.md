# 地图对话范围复查 · 2026-11-15

> 2026-11-17 归档说明：本记录中的测试/构建日期和结果为历史证据；本次整理未重新运行。地图任务的 Saved 临时目录及截图已移入 `trash/map-system-20261117/` 下的原相对路径，详见 [发布与归档清单](../Publication/MapSystem20261117/README.md)。 标记的最终共享语义与真实 UDP 结果以 [后续共享记录](map-marker-sharing-20261115.md) 为准，覆盖旧版本的“仅个人”说明。


本次用户明确要求检查本对话的完成情况、遗漏和 bug，重点为联机。保留现有冷钢 UI、10 个个人标记、个人迷雾和移动规则；后台检查，不打开交互编辑器，不修改玩家档案或联系其他任务。

## 覆盖清单

| 需求 | 复查入口与边界 |
| --- | --- |
| M 地图、实际俯视底图、位置对齐 | `FPSGAMEGameMenu`、`ColdSteelWorldMapData`、主神空间贴图注册信息、地图投影/反投影；丘陵独立材质捕获与等高线。 |
| 打开地图时继续移动 | GameAndUI、移动按键转发、视角屏蔽；编辑标记独立持有移动屏蔽计数，取消/销毁释放自己的计数。 |
| 战争迷雾、坡道、上下层和门 | `ColdSteelDungeonMap` 的三维路线投影、脚下支撑、分层补丁与遮挡碰撞；运行已有几何检查。 |
| 主客机探索隔离、返程/重进/新局 | 本地控制器绑定、逻辑区域、传送 token、RunId/流送关卡身份；共享任务进度不驱动个人揭雾。 |
| 标记/标签、颜色、光柱和顶部方位条 | `ColdSteelMapMarkers`、`SColdSteelMapMarkerEditor`、`ColdSteelHUDNavigation`；私有会话、容量、ViewTarget 拥有者、无复制、楼层和区域过滤。 |
| 地图 UI 升级 | 画布内浮层、固定标签栏、缩放/定位、已探索楼层选择；先前紧凑编辑浮层与最终画面复核被用户中断，不能当作已验收。 |
| Buff 与任务栏显隐 | 本地控制器地图开关统一入口；恢复时重新读取状态/任务快照，不修改效果计时或共享任务进度。 |

## 已发现并修复

**P1：联机加载接管输入前，未关闭地图。** 队友发起出征时，`ClientBeginRoomEntry` 进入 `BeginRoomTransition`；旧实现只关闭出征/木工面板，加载层直接改输入模式。加载结束 `RestoreGameplayInput` 又清除输入屏蔽并回到 GameOnly，但地图及其 HUD 隐藏状态仍可能保留，编辑标记也可能残留。

修复：`TransitLoadingSubsystem::CaptureLoadingInput` 在接管焦点前调用所属本地控制器的 `CloseGameMenu`，沿已有关闭链路释放地图/编辑器、恢复 Buff 和任务栏、释放本次输入计数。标记编辑器恢复输入前也检查加载层是否仍拥有光标，避免晚到取消夺走加载焦点。未改房间 RPC、任务推进或迷雾共享规则。

## 检查证据与范围

- 基线 `ColdSteelDungeonFogCheck -NetworkLifecycle`：26 项检查、0 失败、进程退出 0。覆盖个人探索隔离、返回主神空间、同位置重入、共享任务进度、新实例与旧实例/旧进度拒绝。日志：`Saved/MapConversationAudit20261115/fog-lifecycle.log`。
- 几何 `ColdSteelDungeonFogCheck`：1034 项检查、0 失败、进程退出 0。覆盖折返/双向坡道、上下层及边沿、实际安装模块的碰撞、不同旋转角度的关门遮挡、开门后同位置重新采样及已探索记录保留。日志：`Saved/MapConversationAudit20261115/fog-geometry.log`。
- 扩展夹具最终运行：**54 项检查、0 失败、进程退出 0**。覆盖个人标记互不混入、10 个上限/满额编辑、颜色与文字处理、真实光柱 Actor 的不复制/视角拥有者、重生重绑、返程隐藏/同局恢复、实例退役清理与保留主神空间标记，以及已保存主神空间底图与注册信息。日志：`Saved/MapConversationAudit20261115/fog-markers-lifecycle-verified.log`。无界面进程未初始化 Slate，编辑取消/销毁的三个输入计数用例明确跳过，仅保留源码审查结论。
- 扩展夹具前两次运行均为 54 项、2 失败、退出 4，日志 `fog-markers-lifecycle-final.log`、`fog-markers-lifecycle-diagnostics.log` 均保留。诊断确认是夹具问题：未创建正常游戏自动创建的相机管理器（视角目标一直为控制器）；NullRHI 无 GPU 平台纹理尺寸（0×0），而保存的源图为 2048×2048、注册宽度为 10477 cm。已补齐相机管理器并读取源图尺寸，未修改生产逻辑以迎合断言。
- 这些生命周期检查使用同一隔离 World 中的模拟监听/客机角色，无网络 socket。真实 UDP、弱网/丢包、互联网连接与最终光柱/浮层视觉效果不在其通过声明内。
- 个人标记和个人迷雾按原合同只保存在本地控制器会话，断线重连或重启后不恢复；这是原定边界，未将其擅自扩展为共享或持久存档。

## 构建衔接记录

- 扩展夹具首次编译暴露 `auto*` 无法从 UE 5.8 的 `TObjectPtr<APawn>` 推导的问题，已改为显式 `APawn*`；这属于检查夹具的编译修正。
- 本轮初次 Editor 构建因上述错误不能成功，已停止本任务自己的构建并保留 `FPSGAMEEditor-build.log`。最终 Editor/Game 构建按共享通道排队，日志计划为 `FPSGAMEEditor-build-final.log` 与 `FPSGAME-build-final.log`。
- 另一项 UE 构建曾占用通道，其低优先级编译进程长期几乎未获得 CPU。原占用释放后曾撤回优先级确认；用户随后明确允许提升当前编译子进程优先级。后续仅按授权提升编译子进程至 Normal，不终止其他任务或修改其文件。
- 最终构建与扩展检查已完成，结果见本记录；这不替代真实双端网络、交互与画面验收。
- `FPSGAMEEditor-build-final.log` 的完整构建退出 6：地图相关源文件及扩展夹具编译成功，但共享工程出现技能树函数解析/接口与丘陵检查夹具参数遮蔽错误。接口及参数已由并行改动补齐；本轮另将 `ColdSteelSkillTreeModel.cpp` 的两个 `SpecRank` 调用限定为已有 `ColdSteelSkillTree::SpecRank`，消除成员函数遮蔽，不改技能逻辑。重试日志为 `FPSGAMEEditor-build-complete.log` 和 `FPSGAME-build-complete.log`。
- 后续并行修正已补齐技能树编译接口；链接仍遇到旧目标文件持有旧符号。只移除并重建 `Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/` 下的 `ColdSteelPlayerState.cpp.obj`、`Module.FPSGAME.1.cpp.obj`、`Module.FPSGAME.38.cpp.obj`，未清理源码、资产或其他缓存目录。
- 生产修复的 Editor/Game 构建 `FPSGAMEEditor-build-05.log`、`FPSGAME-build-05.log` 均为 `Succeeded`。夹具修正后的最后构建 `lifecycle-final-FPSGAMEEditor.log`、`lifecycle-final-FPSGAME.log` 也均为 `Succeeded`，DLL 和 EXE 均已链接落盘。

## 完成结论

本对话的地图功能及 HUD 显隐已接入源码和构建产物；本轮发现并修复一处联机加载衔接问题。几何与个人会话生命周期检查通过。

仍不能标记为实机验收完成的部分：真实双端 UDP/弱网下的地图流程；最终光柱、紧凑标记编辑浮层的画面；实际键鼠开关地图、编辑标记以及 Buff/任务栏恢复。后台检查未打开交互编辑器或游戏，也未改写玩家存档。此前关于 Fab/GitHub 的选型记录仍在 `world-map-plan-20261113.md`，最终实现采用项目原生 Slate 与场景/地牢布局数据。
