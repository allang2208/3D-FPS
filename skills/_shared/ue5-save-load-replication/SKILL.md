---
name: ue5-save-load-replication
description: UE5.6-UE5.8 save/load and multiplayer replication workflow for gameplay systems. Use when requests involve SaveGame schema design, serialization, restore pipelines, RepNotify handling, RPC entry points, and server-authoritative validation.
---

## 执行约定

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

遵守用户全局规则：后台制作、不主动测试、不跨对话协调。涉及 UE 构建或资产操作时，按需读取[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)；已读则复用。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

# Quick Start

地牢与主神空间并存、房主单独返程、个人奖励确认及实例库存隔离，读取 [同房间地牢与个人返程](references/individual-dungeon-return.md)。

- 焚化炉、弹药暂存、永久销毁确认及晚到回执／重连绑定清理，读取 [永久销毁与暂存恢复](references/destructive-inventory-and-escrow.md)。

- 装备符文的远端材质、攻击耗体与武技冷却确认，读取 [装备符文与攻击提交回执](references/equipment-runes-and-attack-receipts.md)。

- FPSGAME 物品占格改变、旧地面物品、客机重连与共享容器旧键迁移，读取 [占格迁移覆盖](references/inventory-footprint-migrations.md)。

- FPSGAME 监听服务器的事务、断线、重生及换图恢复，读取 [生命周期与覆盖记录](../ue5-cpp-gameplay/references/multiplayer-lifecycle-and-coverage.md)。

- FPSGAME 搜索容器的共享库存、领取标记、事务日志和访问校验，读取 [设施搜索容器](../ue5-world-interaction/references/facility-search-containers.md)；普通存档任务不必加载该项目案例。
## 存档与复制合同

- 先分清个人档案、共享世界和临时会话状态，并标明各字段是否保存、复制或由其他值派生。原因：磁盘持久化和网络同步有不同生命周期，混用会把临时缓存恢复成正式状态。
- 沿用工程现有存档格式、稳定 ID 和版本迁移；只为本次数据变化增加必要迁移，不强制改为 `USaveGame`。原因：已有 JSON、二进制或影子档案消费者需要保持兼容，按新模板替换会破坏旧档。
- 按依赖恢复拥有者及其对象，异步回调使用当前对象和会话身份。原因：晚到回调或依赖缺失可能把旧世界数据写入新实例。
- 保存操作沿用现有同步/异步写入和成功回执，失败不发布已提交状态。原因：界面显示成功前必须对应实际持久化结果，重试不能重复发奖或扣除。
- 共享玩法仍由服务器结算；客户端通过已存在的请求入口表达意图，服务端使用权威对象、距离、费用和轮次处理。原因：客户端本地显示和档案输入不能替代共享世界的结算依据。
- 复制只携带需要传给该客户端的状态；`OnRep` 负责重建表现，不重复做权威扣费或奖励。原因：复制回调可能因重连或状态更新再次触发。
- RPC 传递请求与回执，持久状态由现有复制和存档路径负责；不因文档模板强制给每个字段增加 `OnRep`。原因：一次性消息无法代替晚加入状态恢复，普通复制字段也未必需要副作用。
- 按工程当前网络系统和引擎头文件选择接口，不预设 Iris 已启用，不承诺跨版本接口完全一致。原因：插件启用情况和项目复制配置决定实际可用路径。
- 制作期间处理必要构建错误；仅在用户要求时执行存档迁移、联机或回归检查。原因：数据兼容性要求仍需在实现中遵守，但它不自动扩大本次测试授权。

API 定位线索：现有 SaveGame 路径可参考 `UGameplayStatics` 的同步/异步 slot 接口；属性复制可参考 `GetLifetimeReplicatedProps`、`DOREPLIFETIME` 和项目已有 RPC。它们是查找接口的线索，不要求改写现有序列化架构。原因：复用工程当前消费者比引入第二套状态来源更容易保持行为。

## 持续技能的保存顺序

弓持续拉弓的同版本档案退款、取消检查点、旧准备回执与失败射击收尾，读取 [弓系准备技能](../ue5-skill-magic-workflow/references/bow-prepared-skills.md#权威资源与取消)。

FPSGAME 持续魔法的施法身份、预测确认、权威奖励模型及断线／换图先结算后保存，读取 [持续魔法的联机状态与收尾](../ue5-skill-magic-workflow/references/persistent-magic-network.md)。

区域首领目标、允许队友入场的方向闸门及每位玩家的区域追踪，读 [区域首领联机规则](references/regional-boss-objectives.md)。

## 近战防御动作的网络身份

复用剑/工具格挡、旧轮次回执、攻击互斥、客机中断与复制破防，读取 [近战格挡轮次](references/melee-guard-intent.md)。 原因：格挡轮次与迟到回执必须共用动作身份，专门参考集中记录跨执行器的中断和复制边界。

## 第三人称武器表现

- 非手枪副手换弹代价漏算、旧书/工具动作套到新实例，以及双持消耗品的手部所有权，读取 [手枪与副手书的联机边界](../ue5-fps-arms-animation/references/pistol-book-ads-and-reload.md#联机与交付)。区分隔离权威检查与真实传输验收。

远端静止瞄准、装备／身体态乱序、机械支撑手与激光落点的身份约束，以及受控联机检查的覆盖边界，读取 [全身表现的联机瞄准与接触](../ue5-cpp-gameplay/references/player-world-body.md#联机瞄准与接触)。

- 弓换手、双手进食收弓及事件滞留的复制边界：[弓与消耗品表现同步](../ue5-cpp-gameplay/references/player-world-body.md#弓换手与消耗品恢复的表现同步2026-10-18)。

- 移动怪物延迟命中、弱点遮挡及器官生命池：读取 [monster-delayed-hit](references/monster-delayed-hit.md)。

- S12K 试装历史导致的复制清单差异与第三人称方向：[S12K 试装历史导致的复制清单差异与第三人称方向](references/saiga12k-presentation.md)。按问题读取；历史检查不授权自动重测。

## 提前准备的怪物实例

处理服务端延迟生成、激活复制、区域分路和取消清理时，读 [区域提前准备的联机边界](../ue5-performance-packaging/references/area-spawn-preparation.md#联机与延迟初始化边界)。客户端资产或 PSO 已加载不代表每实例蒙皮缓冲已经准备；构建结果与主客机运行覆盖分别交付。

- SVCH 改造历史引起远端部件编号差异，或核对近战/换弹的联机检查范围：读取 [SVCH 配件身份与联机覆盖](references/svch-presentation-coverage.md)。区分隔离权威、实际 UDP 和完整实战流程。

- 装备穿戴已更新但旧物品／共享掉落物仍显示旧版，读取[旧装备实例与外观路径](../asset-model-workflow/references/continuous-boots-and-render-lods.md#装备接入与旧实例)，保留实例属性并区分监听主机、重连及未覆盖的网络模式。

## 手枪装填与弹药对账

补弹后射击被拒、切弹种首发不一致、左轮中断或双枪共享弹池时，读 [手枪装填权威](references/pistol-ammo-authority.md)。表现复制与实际弹药结算分开核对。

## 场景家具与表现同步

可重复开关的柜体、多人查看者生命周期、坐卧晚加入及设备/环境动画时钟，读取 [场景动作与查看者](references/scene-motion-and-viewers.md)。库存事务与表现状态分别维护；需要检查时才启用案例中的多进程夹具。
- 性别/头型切换被旧档案回传撤销，或物品操作吞掉外观上传：[外观选择与档案回执](references/appearance-profile-sync.md)。

- 装备数值改版、旧腰带强化迁移及远端动作加速，读取 [装备目录迁移与远端动作时钟](references/equipment-tuning-and-clocks.md)。

- 近战冲刺前踏、空中惯性、攻击 RPC 与 CMC 移动包乱序，读取 [战锤冲刺移动身份](references/hammer-sprint-movement.md)。区分隔离权威检查、实际 UDP 与最终画面覆盖。

篝火食品保鲜、共享订单、F6 免食材与回执锁定，读取 [篝火食品与交易回执](references/campfire-food-transactions.md)。

- M24 不同试装历史的部件身份、原生轴与 FX socket，以及本地 UDP 的覆盖边界：[M24 表现身份](references/m24-presentation-identity.md)。

- 复制字段遗漏、短暂接触事件与真实 UDP 覆盖：读取[复制字段遗漏、短暂接触事件与真实 UDP 覆盖](references/replicated-terminal-events.md)。

- 架枪请求绑定、RPC 与属性回执交错、取消和服务器安装资格，读取 [脚架请求与确认](references/bipod-request-confirmation.md)。

- 进食、饮水与药水的客机取消、最早结算点和迟到回执见[消耗品结算回执](references/consumable-contact-receipts.md)。

- 狙击开火快照、远端短眩晕、枪声与 AI 听觉：读取 [狙击开火快照、远端短眩晕、枪声与 AI 听觉](references/sniper-launch-and-short-stun.md)。

涉及快速近战身份与实际联机检查时，读取 [快速近战身份与实际联机检查](references/quick-combat-authority.md)。

- 强化台真实暂存、旋转占格与种植同版本快照乱序，读取 [强化暂存与种植快照顺序](references/enhancement-escrow-and-planting-order.md)。

## 环境动物受击与尸体复制

连续同状态受击、方向选择、晚到动作与客户端尸体表现，读取 [环境动物动作快照](references/wildlife-action-snapshots.md)。

## 动物掉落队列与离场保存

处理合批掉落、换图或正常退出时，读 [待提交动物掉落](references/pending-wildlife-loot.md)，不要只保存已生成的拾取物。 原因：「待提交动物掉落」记录该任务的专属入口和边界，按主题引用可避免另写一套相互冲突的步骤。

## 类玩家敌人的生命与结算

未知的客机受伤、迟到攻击、死亡重生、晚加入和换图清理，读取 [类玩家怪物的伤害与生命周期](references/unknown-combat-lifecycle.md)。

地图系统的私有/全队标记、个人迷雾和地牢实例边界，读取 [标记共享与个人探索](references/map-markers-and-personal-fog.md)。

丘陵生成地面、客机直达和内容版本兼容，读取 [丘陵生成地面、客机直达和内容版本兼容](references/hills-generated-ground-network.md)。

丘陵监听服的种子归属、工匠货架竞争和个人修炼进度见[房主存档、共享货架与学徒任务](references/artisan-village-session-and-stock.md)。

伙伴名册与装备归属参见[伙伴名册与装备归属](references/owned-equipment-and-roster.md)。
