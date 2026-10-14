# 联机覆盖台账与中断恢复（2026-10-14）

本台账对齐历次记录，区分本轮复读、历史检查、仅登记和用户运行测试。没有用“已检索到文件”代替逐行审阅，也没有把全部引擎插件登记数量当作玩法审查数量。

## 本轮确认并修复

| 分支 | 原先的遗漏 | 修改与恢复行为 |
| --- | --- | --- |
| 锻造、枪械拼装、木工退出镜头 | 退场优先返回仍有效的旧 PreviousView；重生后旧 Pawn 仍有效时可覆盖新角色镜头。锻造/拼装没有处理尚在淡入的 PendingViewTarget | 三者共用小型恢复函数，处理当前及待切入视角；控制器已换 Pawn 时立即回到新 Pawn，无 Pawn 时释放到控制器，不回到旧角色 |
| 失去控制器后的 PlayerState 销毁 | EndPlay 依赖当时的 Owner；Owner 已解除且没有库存请求时，漏掉本地工作站清理 | 记录曾经的本地归属，销毁时清理木工/锻造/拼装运行态、商店会话、共享容器临时视图与库存等待标记；不清理其他玩家的本地模型 |
| 枪械拼装暂停 | 客机只保存本地镜像，不通知服务器暂停；不足 0.1 秒的一批校准输入可能丢失，或残留到下次工件 | 校准批次绑定 Pawn 与工件 ID；同一角色/工件暂停时提交尾批，再发暂停输入，服务器保存影子档案。换角色/工件清空未发送尾批；断线/换图收尾也包含拼装 Pause |
| 离开工作台后的收尾 | 普通工作站输入的距离门槛也拦截暂停保存 | 暂停在 Pawn/工件核对后可执行；增加进度的输入仍要求工作台可达，离台不增加校准成绩 |
| 加入/连接失败 | 只改变菜单标记，旧遮罩、准备对象和输入持有未立即释放；没有 View 时 IsTickable 也不保证再次显示菜单 | 失败时解除旧准备与遮罩；待显示错误本身保持菜单恢复调度，返回单机世界后展示错误 |
| 房主收到客机连接故障 | 同 World 的网络失败回调可能把监听服务器也置回启动菜单状态 | 连接故障不重置房主启动状态；服务器换图失败只释放过场并提示错误，整队准备仍由既有旅行协调器解除 |

这些修改不改变配方、材料费用、成品质量公式、角色存档格式或工作站布局。异常断网发生前尚未发出的输入无法凭空恢复；本轮保证正常暂停提交尾批、断线清理临时输入，保留服务器已收到的进度。

## 源码功能与异常分支

| 功能域 | 当前覆盖依据 | 本轮状态 |
| --- | --- | --- |
| 登录、退出、房间缓存、重复档案 | [生命周期与并发](lifecycle-concurrency-assets-20261013.md)、[重连重生换图](reconnect-respawn-travel-20261013.md)、[交易交接](transaction-disconnect-handoff-20261014.md) | 复读 WorldSubsystem、GameInstance 房间缓存与 PlayerState EndPlay；补本地清理归属 |
| 档案分块、库存回执、临时容器视图 | [移动与档案拥塞](movement-profile-congestion-20261013.md)、[库存/冷却恢复](inventory-cooldown-station-recovery-20261013.md) | 复读分块容量、回执解锁、Pawn/库存版本和临时视图剥离；补退出清理 |
| 扣费、领取、持久保存、换图交接 | [交易断线交接](transaction-disconnect-handoff-20261014.md) | 沿用具名提交链路检查；本轮不重新宣称磁盘故障经过运行注入 |
| 工作站开始、输入、暂停、领取、废弃 | [世界功能](world-feature-repairs-20261013.md)、[库存/工作站恢复](inventory-cooldown-station-recovery-20261013.md) | 复读服务器输入和三种交互视角；修复暂停尾批、保存、角色更换及销毁分支 |
| 异步制作表现、资源取消 | [动态加载](dynamic-loading-lifecycle-20261013.md) | 复读锻造/装配/木工资源委托及销毁、工具架/锯片组件取消、地牢 GenerationSerial 与 CancelAssembly；未新建异步框架 |
| 玩家移动、闪避、攀越、输入反馈 | [玩家动作](player-actions-and-spellbook-20261012.md)、[基础覆盖续查](basic-coverage-followup-20261013.md)、[门与脚架](door-push-bipod-20261003.md) | 沿用历史指定入口；本轮镜头恢复覆盖新旧 Pawn 交接 |
| 枪械、近战、弓、工具、武技 | [近战与档案镜像](client-melee-and-profile-mirror-20261013.md)、[武器表现](weapon-animation-sync-20261013.md)、[武技/快捷栏/弹药恢复](martial-quickbar-ammo-recovery-20261013.md) | 沿用历史指定入口；未把镜头清理扩大为武器动作重制 |
| 主动法术、资源预留、取消 | [扩展覆盖](extended-coverage-repairs-20261013.md)、[库存/冷却恢复](inventory-cooldown-station-recovery-20261013.md) | 本轮复读 PlayerState 未释放法术的死亡/Pawn 更换清理；其它施法时序沿用历史记录 |
| 怪物、受击、特殊攻击 | [全项目原生入口](project-wide-source-sweep-20261013.md)、[怪物动作分支](monster-action-branches-20261014.md)、[格挡反馈](guard-feedback-repairs-20261013.md) | 上一批七项具体分支已修复并构建；不把基类复制当作全部派生类已审阅 |
| 采集、建造、倒塌、门窗、宝箱、神龛 | [十一类补漏](coverage-repairs-20261013.md)、[战斗与世界同步](combat-and-world-sync-repairs-20261013.md)、[全项目原生入口](project-wide-source-sweep-20261013.md) | 沿用既有权威请求、共享状态及持久记录；本轮对齐场景实例读取范围 |
| 地牢进度、运行时生成、迟到场景对象 | [动态加载](dynamic-loading-lifecycle-20261013.md) | 复读取消标记、世代编号、资源句柄取消和玩家释放；资产引用范围刷新见下 |
| 天气、水面、脚步及环境表现 | [全项目原生入口](project-wide-source-sweep-20261013.md)、[蓝图/流送/插件](blueprint-streaming-plugin-coverage-20261013.md) | 本轮复读 AutoFootstep 弱上下文与旧世界拒绝；其余沿用历史指定入口 |

## 蓝图、地图与插件证据对齐

本轮通过 `MultiplayerAssetInventory -ReferencesOnly` 刷新注册表；随后按 `AssetList` 只读取选定资产，工具不调用 BeginPlay、不执行游戏事件图、不保存 Content 包。扩展的 AssetList 参数用于避免反复加载无关演示资产。

- 当前登记 42,780 个包，上一份登记为 42,751 个；当前启用插件仍为 296 个，没有新增/移除插件。
- 从主地图入口计算的引用闭包仍为 6,093 个包。当前清单包含 46 个地图包；比旧的 45 个场景清单多纳入 `/Game/MilitaryTrench/Tutorial/Scenes/Scene_Trench_Tutorial`。这是包依赖扩展，不能直接认定它是新增游戏玩法入口。
- 发现 3 张已引用地图和 `BP_BellowSacLobber` 的文件修改时间晚于旧资产读取；本轮请求复读 46 张图和该蓝图，共 47 个包。修改时间筛选用于定位复读对象，不是旧资产字节散列一致性的证明。
- 用户关闭编辑器后，47 个请求包已全部复读，输出为 `Saved/MultiplayerInterruptionCoverage20261014/assets-current.json`：46 张地图、28 个蓝图对象（包含内嵌关卡脚本）、7,430 条 Actor 记录，加载失败 0，待复读包 0。所读实例没有关闭原生复制、移动复制或客户端加载的覆盖值，没有客户端专属可见流送层。
- 蓝图执行连线及地图脚本/流送配置与具名旧记录比较未发现新增变化，结果为 `asset-graph-changes.json`。Normandy 五个常驻层使用后续 `scene-details.json` 的同字段记录比较，避免把读取工具后来新增的 `client_only_visible=false` 误报为资产修改。
- 本次资产读取退出码 0，日志为 `Success - 0 error(s), 188 warning(s)`。警告涉及第三方素材空引擎版本、编辑器建模接口 Python 重名及无界面工具状态；没有据此重存第三方资产或修改无关编辑器插件。资产存在、可静态读取与运行时联机正常仍是不同结论。
- `AutoFootstep`、`ColdSteelNet` 是当前登记中位于项目 Plugins 目录的运行模块；本轮读取其脚步异步回调、连接测试钩及 GameMode 生命周期。没有新增插件代码修改。`MPConnect` 是显式命令行测试钩，默认无目标时不启用，不视为自动重连产品功能。
- `AdaptivePathfindingSystem`、引擎 PCG 和其余启用插件保留[上一轮插件归类](blueprint-streaming-plugin-coverage-20261013.md)；登记与宿主接入检查不等于逐行审核插件内部实现。Editor-only 工具不改造成游戏 RPC。

## 旧记录中的待办如何解释

| 旧记录的未覆盖项 | 后续记录或当前边界 |
| --- | --- |
| `basic-feature-repairs` 尚待采集、建造、工作站、神龛、组队换图 | 已由 `world-feature-repairs` 接入，后续批次继续补漏；旧文字保留为当时状态 |
| `project-wide-source-sweep` 未读全部蓝图/流送/插件资产 | 后续 `blueprint-streaming-plugin-coverage` 已静态读取 718 独立蓝图、30 内嵌脚本、141 地图；本轮刷新引用与指定资产，不把历史数量写成本轮全量重读 |
| `lifecycle-concurrency-assets` 钥匙只在当前 World 缓存 | `reconnect-respawn-travel` 已改为带房间标识的 GameInstance 缓存；服务器进程重启后的会话钥匙仍不属于持久存档 |
| `lifecycle-concurrency-assets` 尚未覆盖 104 张旁支地图 | 后续全量资产读取及场景闭包读取已有记录；素材演示可加载不等于已成为正式联机入口 |
| 8 个旧示例/编辑工具蓝图编译错误 | 仍按先前引用归类保留，不计作正式玩法修复完成，也未擅自升级示例工程 |
| World Partition 外部单元、专用服、主机迁移、自动重连 | 世界分区运行未执行；后面三项未实现为产品能力，当前支持边界仍为主机开房/客机加入 |
| 打包跨机、外网、高延迟/丢包、长时间并发 | 用户运行测试范围，本轮未执行 |

## 构建与交付

本轮涉及 12 个源码文件（含 1 个新增相机恢复头文件）。修改前备份、差异、源文件散列、资产登记回执均在 `Saved/MultiplayerInterruptionCoverage20261014/`。

- `FPSGAMEEditor Win64 Development` 首轮成功，87 个动作，110.73 秒。用户关闭编辑器后的最终构建于 2026-10-14 12:24:59 完成，4 个动作，26.71 秒，退出码 0，`Result: Succeeded`；已编译最后的房主换图失败分支并重新链接项目 DLL，日志为 `editor-build-closeout-output.txt`。
- `FPSGAME Win64 Development` 首轮成功，103 个动作，139.92 秒。追加修改后的最终 Game 构建也成功，3 个动作，48.38 秒，退出码 0；日志为 `game-build-final-output.txt`。
- 全量资产注册表读取 `references-current-result.json` 退出码 0；没有加载并验收全量玩法资产。
- 选定资产内容复读于 2026-10-14 12:26:12 完成，`assets-current-result.json` 退出码 0，统计为 `asset-read-summary.json`；先前的编辑器占用已解除，没有自动重开编辑器。
- 24 份 Markdown 批次记录索引为 `record-index.json`；当前资产范围与逐包状态为 `coverage-reconciliation.json`，源文件变更为 `source-manifest.json` 与 `changes.patch`。

覆盖台账已按具名证据归并；这不是全项目所有函数与任意网络时序的无遗漏证明。没有启动交互式编辑器、PIE、游戏或自动回归，实际联机表现由用户测试。
