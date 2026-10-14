# 基础功能联机排查（2026-10-13）

## 范围与结论

按用户要求，检查监听服主机＋客机的基础入口、玩家档案归属、服务器请求、结果回传和保存路径。覆盖移动、装备、枪械／近战／弓、快捷栏、消耗品、掉落、容器、世界交互、制作、出征、死亡与复活。

结论：目前不能称为基础功能完整支持联机。除了已修复的移动断流与客机唐刀初始化，还存在明确禁用的功能，以及本地操作和服务器结算没有接通的功能。以下为源码证据，不是双人实机通过记录；本轮没有启动 UE、游戏、PIE 或自动回归。

## 本轮已修改的四处问题

| 功能 | 原因 | 本轮修改与边界 |
| --- | --- | --- |
| 监听服主机火球 | `Skills/FPSFireballComponent.cpp::Trigger` 在已有本机控制判定后，只允许 Standalone／Client，把 ListenServer 排除 | 移除多余模式排除；主机沿既有权威生球／发射分支，客机仍走 ServerCastSpell。没有改动画、蓝耗或伤害 |
| 法杖初始装备归属 | `Weapons/Staff/StaffWeaponComponent.cpp::BeginPlay` 给每个 pawn 读 GameInstance 的本机档案 | 本机角色用本机档案，服务端远端角色用其影子档案；客户端远端代理不应用本机法杖装备。只修初始化与刷新归属 |
| 客机裂斩刀身视觉 | `Weapons/FPSRiftBladeComponent.cpp::BeginPlay` 直接拒绝 Client | 客机允许初始化表现，Tick 只给本机控制角色创建第一人称刀身视觉；不新增世界伤害或远端特效复制 |
| 影子档案误操作主机掉落 | `UI/ColdSteelProfileRuntime.cpp::AttachPawn → RefreshDrops` 会遍历整个世界，根据当前档案删掉“不属于自己”的拾取 Actor；SyncRuntime 也会按实例 ID 读整世界掉落位置 | 影子档案不再生成／清理本机存档掉落视图，也不从该视图回写位置。这阻止跨玩家干扰；**共享联机掉落仍未接入**，没有将此保护称为共享拾取完成 |

修改前文件保存在 `Saved/MultiplayerBasicsAudit20261013/Before/`。

## 明确仍缺失或不完整的功能

表中路径均相对 `Source/FPSGAME/`。P1 优先解决资源一致性和会话问题；P2 为明确缺少的功能入口／联机流程。

| 优先级 | 功能 | 具体证据与影响 | 完成所需的工作 |
| --- | --- | --- | --- |
| P1 | 客机吃饭、饮水、恢复 SAN | `UI/ColdSteelProfileRuntime.cpp::UseConsumableAtContact` 在本机改 Survival 并扣物品；`Survival/FPSSurvivalComponent.cpp::RestoreState` 只允许权威端；`Multiplayer/ColdSteelPlayerState.cpp::ApplyGuestProfile` 又用服务器 Survival 覆盖上行值。因此本地消耗不能把生存资源恢复交给服务器 | 按物品实例提交使用请求；服务器验证、消耗和恢复，同步结果及拒绝回执。回血／回蓝也应纳入同一事务，不能继续依赖大档案补传 |
| P1 | 共享丢弃、E 拾取、他人物品可见性 | `UI/ColdSteelWorldInteraction.cpp::TraceTarget` 客机只放行原生门和篝火；`UI/ColdSteelPickup.cpp` 原生类不启用复制；`ColdSteelProfileRuntime.cpp::Drop/Pickup/RefreshDrops` 基于个人档案和本地 Actor；`ColdSteelAreaPickup.cpp::PickupNearby` 只改本机档案 | 独立世界掉落实例、服务器所有权、原子拾取／丢弃、数量／销毁复制。Z 本地批量拾取存在，不能据此认为共享拾取可用 |
| P1 | 同机双 PIE 存档隔离 | `UI/ColdSteelProfileRuntime.cpp` 初始化默认 `SaveSlot="ColdSteelPlayer"`，只接受进程级 `-ColdSteelProfile=` 覆盖；没有 PIE 玩家实例后缀。相同进程的两个 GameInstance 默认读写相同 `_A/_B` 文件 | 为测试玩家分离存档身份及路径，并明确初始档案拷贝策略。当前可能发生后保存的一方覆盖另一方，尚未改动用户已有存档 |
| P1 | 组队出征／跨地图 | `UI/ColdSteelExpeditionController.cpp` 明确拒绝客机；主机确认后使用 `UGameplayStatics::OpenLevel`，不是服务器带队换图 | 建立服务器出征请求和 ServerTravel、会话保留、各玩家档案恢复；再检查动态地牢生成与碰撞是否在两端一致。当前不能把主机能进地图当作组队出征完成 |
| P2 | 弓装备、射箭与回收 | `Weapons/Bow/BowWeaponComponent.cpp:134` 拒绝所有非 Standalone 模式，主机和客机都不初始化；箭当前由本地生成，`BowArrow.cpp` 回收又限定 Standalone | 补装备初始化、射击／箭数结算、箭体表现及回收归属。通用命中上报有弓分支，但不能替代完整弓流程 |
| P2 | 快速近战 | `Skills/ColdSteelSkillModel.cpp::CommitQuickCombatCast` 明确在 Client 返回 false；唐刀配重快战及共用快战路径依赖它 | 接上动作请求、服务器体力／动作占用和回执。不能仅删 Client 条件，让服务器跳过成本和合法性处理 |
| P2 | 斧、镐、铲与采集 | `Production/ProductionToolComponent.cpp:65` 禁用客机组件；`ProductionHarvestSubsystem.cpp` 客机直接返回，工具也没有采集 RPC | 同步工具装备，并贯通砍树／采矿／挖填请求、世界修改、掉落和库存。不能仅让手模出现 |
| P2 | 环绕飞剑 | `Weapons/RuneOrbBladesComponent.cpp::CanUse` 明确排除 Client | 服务器召唤／发射／成本／冷却及拥有者表现链；不要把本轮裂斩刀身视觉修复混同于飞剑技能 |
| P2 | 仓库与场景容器 | `UI/ColdSteelWarehouseChest.cpp::CanInteract`、`ColdSteelSceneContainer.cpp::CanInteract`、`ColdSteelWarehouseHUD.cpp` 和容器瞄准函数均拒绝 Client | 定义共享／个人容器归属，补打开请求、内容同步、事务版本和转移回执 |
| P2 | 喷泉、宝箱、祭坛等 E 交互 | 客机瞄准白名单没有放行这些对象；喷泉 `DrinkFromFountain` 还要求 Pawn 权威；地牢神龛拒绝 Client | 按交互对象接入服务器请求与结果。原生门、篝火已有独立联机通路，不在此缺失项内 |
| P2 | 体素建造、锻造、枪械拼装、木工 | `Building/VoxelBuildComponent.cpp:158` 在客机初始化失败；`ForgingSystem.cpp`、`GunAssemblySystem.cpp`、`WoodworkingSystem.cpp` 明确拒绝客机；木工控制器还限定 Standalone | 建造与各工作站的服务器操作、耗材／产物事务、进度和结果复制。现有私人背包可写不等于这些世界功能可用 |

这些项是实际功能缺口，不能通过简单取消 `NM_Client`／`NM_Standalone` 判断全部修复。本轮只完成上述四处可独立收口的修改，没有把整套联机物品经济、制作与团队换图标记为已完成。

## 已找到联机通路的基础项目

以下仅说明源码链存在，仍需实机确认输入、时序和显示。

| 功能 | 当前源码链与限制 |
| --- | --- |
| 普通移动、冲刺、瞄准速度、滑铲、闪避、翻越 | 自定义 CharacterMovement 的 SavedMove／移动包、Traversal RPC 与退出回执已存在；前两轮已修复大档案阻塞移动和出生踩玩家头顶 |
| 唐刀及共用双手剑装备 | 上一轮已补本机／服务端初始化和晚到的控制器路径；快速近战仍有独立禁用项 |
| 普通枪械射击、装填、命中 | 本机动作和通用命中 RPC、服务器武器／速率／几何校验存在；Super90 有专门弹药和装填权威流程。不能由一把枪推断全部枪械已实测 |
| 主副手切换、背包操作、快捷栏 | PlayerController 本机输入、CycleWeapon／UseQuickBinding、个人档案事务及分片上传存在；世界拾取／容器另列缺口 |
| 火球、冰锥、冰墙、暴风雪、圣光、闪电、火系／电系法术 | 组件通过 NetCast／ServerCastSpell 上报阶段，服务器处理及 ClientCastResult 回执存在；本轮补主机火球入口，其他类型未宣称运行通过 |
| 魔法书专注与远端身体 | 专注请求／停止回执、装备与动作样本有对应网络实现；已读前次动作排查记录并确认当前入口 |
| 原生门与篝火 | DoorPush 组件承接开门／推门请求；篝火有独立共享面板 → RequestCampfire → 服务器事务 → ClientCampfireResult／分片镜像。旧冶炼面板中的未接入文字不代表新篝火通路不存在 |
| 玩家受伤、死亡、重生 | Health 复制、客户端死亡停输入、服务器定时销毁旧 pawn 并 RestartPlayer、重新挂影子档案的链存在；未做死亡实测 |
| 多玩家怪物目标与菜单 | 共用 AI 控制器会枚举玩家；Esc 只在 Standalone 暂停世界。未逐个怪物验证个性化 AI，也未把这些正向源码证据等同于所有场景支持 |

## 后续处理顺序

建议先处理：同机测试存档隔离 → 吃喝与药品事务 → 共享掉落／拾取／容器 → 快速近战与弓／工具 → 工作站／建造 → 组队出征及目的地世界同步。这样先解决丢物、扣物无效果和会话中断，再扩展功能范围。

本轮构建与最终状态见 `Saved/MultiplayerBasicsAudit20261013/`；不改现有磁盘存档、不启动实机测试。

正式构建均成功：`editor-build.log` 为 14 个动作、已链接 `UnrealEditor-FPSGAME.dll`；`game-build.log` 为 13 个动作、已链接 `FPSGAME.exe`。两份日志均为 `Result: Succeeded`。本轮四处修改已编入正式产物；上表其余缺口仍未补齐。
