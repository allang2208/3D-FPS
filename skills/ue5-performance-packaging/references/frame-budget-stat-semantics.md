# UE5 帧预算统计的正确读法（引擎源码核对，2026-09-22）

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 1. 线程耗时的两组变量语义不同（源码核对）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 2. `GGameThreadTime` 是帧间隔减空闲，不是「游戏线程干了多久」（源码核对）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 3. 面板经 UI Tick 采样帧时间会截断长卡顿（待验证，来源为外部审查）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 4. GPU 时间不要用 `RHIGetFrameTime()`（待验证，来源为外部审查）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 5. 逐组件耗时与逐图元 GPU 耗时都拿不到（源码核对）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 6. 计数比计时更可得的替代手段（本次采用）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 7. 测量纪律（本次两次假设被推翻后的硬性结论）

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。

## 8. 本项目专用运行时开关

详见[维护源](../../_shared/ue5-performance-packaging/references/frame-budget-stat-semantics.md)中的同名章节。
