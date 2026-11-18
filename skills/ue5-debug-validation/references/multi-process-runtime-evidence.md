# 多进程 UE 检查：运行负载与构建证据

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 工作站联机场景的有效前置

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 固定姿态和消耗品夹具（2026-10-18）

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 持续技能结果的结算时机（2026-10-22）

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 手枪装填夹具（2026-10-24）

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 场景状态夹具与晚加入（2026-10-24）

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 第三人称截图与战斗传输分开计证（2026-10-30）

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 重击加载假设与可控传输复现（2026-11-04）

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## 类玩家敌人的生命、重连与换图夹具

详见[维护源](../../_shared/ue5-debug-validation/references/multi-process-runtime-evidence.md)中的同名章节。

## GC、加入与外部硬件竞争

- 获得性能复查授权后，观察窗口要覆盖实际 GC 周期，并分别记录加载阶段、输入解锁、怪物出现、新玩家加入及退出；首次几秒平滑不能证明后续回收没有卡顿。
- 独立宿主仍共用 CPU、GPU、内存和磁盘。除了 UE/编译器，也记录其他游戏、Insights 导出和大型制作进程；一次总 GPU 利用率不支持具体 pass 归因。需要确认竞争来源时，可对已发现 PID 读取 Windows GPU Engine 计数器。
- Trace 导出和性能采集分开运行。发现外部负载时保留受干扰记录，功能结果与性能结论分开；不得关闭用户游戏或其他任务来制造独占环境。
- 用户暂停时停止本轮拥有的隔离进程，保留 paused 标记和已完成的逐端回执；不要把主动停止产生的脚本失败改写为全轮通过。恢复须另有用户指令，整理/推送不自动恢复检查。
