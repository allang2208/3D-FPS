# M870 完成度与联机检查矩阵

用户于 2026-10-17 明确要求检查遗漏和 bug，重点为联机。使用隔离档案、后台 commandlet 及本机 UDP 监听主机/客机，不修改正常存档，不启动图形编辑器。

| 路径 | 当前检查方式 | 证据/状态 |
| --- | --- | --- |
| 轻量化扳机与延长管 | 目录、真实属性评估、角色应用、特殊改造分类 | authority-result.json |
| 原厂恢复与后握把移除 | 目录槽位与模型端盖切换 | authority-result.json |
| 所有主动作资源 | 当前角色实际加载对象 | authority-result.json；外观与手部接触仍未视觉验收 |
| 第三人称 | 实际装备快照中的手臂隐藏、原厂端盖隐藏、延长管挂点 | authority-result.json + wire host/client |
| 射击权威 | 实际 RPC 实现：三类弹药、总伤害、重复序号、冷却 | authority-result.json |
| 逐发及速装器 | 十发装填、七发速装器限制、再次补三发、守恒 | authority-result.json |
| 泵动中断 | 有效开火对应的中断、待闭锁保存、只泵动恢复 | authority-result.json |
| 新 Pawn 回执 | 拒绝旧 Pawn 弹药回执、清除泵动预测 | authority-result.json；真实死亡/重生尚未双端覆盖 |
| 拆延长管 | 权威容量收缩、实体/虚拟弹药、重复上传只退一次 | authority-result.json |
| 存档 | SaveGame 内存序列化往返保留扳机/延长管 | authority-result.json；断线后实际重连尚未覆盖 |
| 真正的网络传输 | 本机 UDP 主客机六种配置，开火与重复 RPC、弹药回执、散布一致、旁观者弹道 | wire_receipt.json；不等于高延迟/丢包覆盖 |
| 泵动抛壳表现 | 接收权威射击速率并扣除网络年龄 | authority-result.json；不等于音画时序视觉验收 |
| 战术设备、瞄具、握把/后托、图标 | 接入源码及资源引用；本次没有逐件截图 | 保留视觉待验项，不能称全部外观合格 |

## 本轮定位的缺陷

1. `TickSuper90Recovery()` 在新 Pawn 路径没有清除 `M870PredictedPumpInterrupts`，随后回执处理因 Pawn 身份已更新而跳过对应重置。旧生命的待泵动预测可能污染新生命。统一清理预测及 server-ready 集合，等待新 Pawn 的服务器回执。
2. `ClientSuper90Ammo` 在写弹仓、弹药袋和待闭锁前没有核对 `SourcePawn`，只在动作收尾处核对。迟到的旧 Pawn 回执可能先改写新 Pawn 的弹药。现在在身份匹配前等待，不将旧回执合并到不同的 Pawn。
3. 远端 M870 抛壳定时读取旁观端角色的 `EffectiveFireInterval()`；旁观角色没有拥有端完整的枪匠数值。轻量化扳机的泵动可能与抛壳不同步。现在开火多播携带权威泵动速率，效果排队后按接收年龄扣除已过时间，迟到事件立即补发弹壳。

## 修复后的实际结果

- 离线目录/文件引用：78 项，0 失败。
- M870 权威 commandlet：57 项，0 失败，结果已复制为本目录 `authority-result.json`。
- 真实 UDP 主机/客机：`Wire/20261017-105955`，双方各 6 组全部通过；`wire_receipt.json` 的 passed 为 true。
- 第一轮 `Wire/20261017-105423` 因无地板夹具中的重力导致首组角色下落、服务器拒绝距离异常的开火位置。保持正式校验，修正夹具运动冻结，并对隔离进程覆盖 DefaultGravityZ=0 后通过。
- 天气编译阻塞及体素诊断日志字符串已按用户要求修正；Editor 与 Game 均已有成功完整链接记录。下方先前失败日志仅作为历史保留，不代表当前交付仍被阻塞。
- 弹药回执按 Pawn 身份等待再合并，兼顾旧回执隔离及新 Pawn 回执早于占有同步到达的顺序。
- 正常玩家存档未修改；后台测试进程已退出。未做视觉验收、高延迟/丢包压力、完整死亡重生场景与断线重连。

## 先前构建阻塞记录（已解除）

- `offline-result.json`：78 项目录与文件引用检查，0 失败。覆盖当前 13 条主动作、14 条速装器动作、六类瞄具及安装座/活动件、现行静态预加载路径、共享图标、Cook 根目录、两项特殊改造及后握把删除。
- 两次正式 Editor 构建未成功链接：`Saved/BuildEditor/build-20261017-103111.log`（147 个计划动作）和 `build-20261017-103704.log`（36 个计划动作），均为 `Failed (OtherCompilationError)`。本轮修改的 ShotgunAttachmentAuditCommandlet、ShotgunWireAudit、ColdSteelSuper90Authority、FPSWeaponFXComponent 及远端表现文件编译阶段未报告错误；这不等于整目标构建成功。
- 阻塞来自当前天气改动：`FPSUDSBridgeComponent.cpp/.h` 的未声明反射查找函数、只读弱字段指针的布尔使用与重载错误，以及 `LightingConflictValidation`、`WeatherPanelValidation`、`WeatherWorldValidation`、`StormCloudComponent`、`SurvivalClockAuditCommandlet` 仍引用已移除的天气接口。本轮没有修改这些并行文件。
- `authority-result.json` 和 `wire_receipt.json` **本轮未生成**。执行脚本在构建失败后停止，没有拿旧 DLL 跑测试，没有启动主客机。
- 因此本轮状态为：源代码问题已定位并修改；目录/文件引用检查完成；当前修复的运行产物、权威执行检查、真实联机验证仍被构建阻塞。不能宣称 M870 全部完成或联机已通过。

## 恢复入口

需要按同一范围复跑时，执行 `SourceAssets/M870CompletionAudit20261017/build_and_audit.ps1`，按顺序构建当前源码、运行 `ShotgunAttachmentAudit -M870`，再运行本机 UDP 监听主机+客机六配置检查。共用批次互斥，档案独立，只有该脚本自己创建的进程会被收尾。

主客机夹具运行正式开火/弹药 RPC，但将测试配置固定在双方档案；改造上传与缩容回放由权威执行用例另测。它不覆盖完整游戏 UI 操作、真实断线重连、死亡重生场景、高延迟/丢包和手部/材质的视觉验收。
