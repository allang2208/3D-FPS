---
name: ue5-save-load-replication
description: UE5 save/load and replication workflow for persistent state, server authority, RPCs and reconnect or travel recovery.
---

# 联机存档与恢复

地牢与主神空间并存、房主单独返程、个人奖励确认及实例库存隔离，读取 [同房间地牢与个人返程](references/individual-dungeon-return.md)。 为什么：「同房间地牢与个人返程」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

焚化炉、弹药暂存、永久销毁确认及晚到回执／重连绑定清理，读取 [永久销毁与暂存恢复](references/destructive-inventory-and-escrow.md)。 为什么：工作区及索引包含其他任务成果，精确发布才能保留各自修改与提交边界。

本机维护源：[ue5-save-load-replication](../_shared/ue5-save-load-replication/SKILL.md)。遵守工程 AGENTS.md、WORKFLOW.md 和本次用户授权，不自动启动编辑器或测试。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

FPSGAME 主客机归属、事务中断、重连／重生／换图、工作站恢复及覆盖记录，读取 [生命周期与覆盖记录](../ue5-cpp-gameplay/references/multiplayer-lifecycle-and-coverage.md)。该参考可跨机器读取；历史构建不代表当前运行验收。 为什么：「生命周期与覆盖记录」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 持续技能的保存顺序

弓持续拉弓的同版本档案退款、取消检查点、旧准备回执与失败射击收尾，读取 [弓系准备技能](../ue5-skill-magic-workflow/references/bow-prepared-skills.md#权威资源与取消)。 为什么：「弓系准备技能」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

FPSGAME 持续魔法的施法身份、预测确认、权威奖励模型及断线／换图先结算后保存，读取 [持续魔法的联机状态与收尾](../ue5-skill-magic-workflow/references/persistent-magic-network.md)。 为什么：「持续魔法的联机状态与收尾」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

区域首领目标、允许队友入场的方向闸门及每位玩家的区域追踪，读 [区域首领联机规则](references/regional-boss-objectives.md)。 为什么：「区域首领联机规则」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

物品占格改变、旧地面物品、客机重连与共享容器旧键迁移，读取 [占格迁移覆盖](references/inventory-footprint-migrations.md)。 为什么：「占格迁移覆盖」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

装备符文的远端材质、攻击耗体与武技冷却确认，读取 [装备符文与攻击提交回执](references/equipment-runes-and-attack-receipts.md)。 为什么：发布目标与本地历史可能变化，明确目标可避免把其他历史推到错误分支。

## 近战防御动作的网络身份

复用剑/工具格挡、旧轮次回执、攻击互斥、客机中断与复制破防，读取 [近战格挡轮次](references/melee-guard-intent.md)。 为什么：「近战格挡轮次」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 第三人称武器表现

远端静止瞄准、装备／身体态乱序、机械支撑手与激光落点的身份约束，以及受控联机检查的覆盖边界，读取 [全身表现的联机瞄准与接触](../ue5-cpp-gameplay/references/player-world-body.md#联机瞄准与接触)。 为什么：发布目标与本地历史可能变化，明确目标可避免把其他历史推到错误分支。

- 弓换手、双手进食收弓及事件滞留的复制边界：[弓与消耗品表现同步](../ue5-cpp-gameplay/references/player-world-body.md#弓换手与消耗品恢复的表现同步2026-10-18)。 为什么：「弓与消耗品表现同步」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 移动怪物延迟命中、弱点遮挡及器官生命池：读取 [monster-delayed-hit](references/monster-delayed-hit.md)。 为什么：「monster-delayed-hit」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- S12K 试装历史导致的复制清单差异与第三人称方向：[S12K 试装历史导致的复制清单差异与第三人称方向](references/saiga12k-presentation.md)。按问题读取；历史检查不授权自动重测。 为什么：「S12K 试装历史导致的复制清单差异与第三人称方向」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 提前准备的怪物实例

处理服务端延迟生成、激活复制、区域分路和取消清理时，读 [区域提前准备的联机边界](../ue5-performance-packaging/references/area-spawn-preparation.md#联机与延迟初始化边界)。客户端资产或 PSO 已加载不代表每实例蒙皮缓冲已经准备；构建结果与主客机运行覆盖分别交付。 为什么：文件保存、编译成功与运行效果对应不同证据，不能相互代替。

- SVCH 改造历史引起远端部件编号差异，或核对近战/换弹的联机检查范围：读取 [SVCH 配件身份与联机覆盖](references/svch-presentation-coverage.md)。区分隔离权威、实际 UDP 和完整实战流程。 为什么：发布目标与本地历史可能变化，明确目标可避免把其他历史推到错误分支。

- 装备穿戴已更新但旧物品／共享掉落物仍显示旧版，读取[旧装备实例与外观路径](../asset-model-workflow/references/continuous-boots-and-render-lods.md#装备接入与旧实例)，保留实例属性并区分监听主机、重连及未覆盖的网络模式。 为什么：「旧装备实例与外观路径」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 手枪装填与弹药对账

补弹后射击被拒、切弹种首发不一致、左轮中断或双枪共享弹池时，读 [手枪装填权威](references/pistol-ammo-authority.md)。表现复制与实际弹药结算分开核对。 为什么：「手枪装填权威」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 场景家具与表现同步

可重复开关的柜体、多人查看者生命周期、坐卧晚加入及设备/环境动画时钟，读取 [场景动作与查看者](references/scene-motion-and-viewers.md)。库存事务与表现状态分别维护；需要检查时才启用案例中的多进程夹具。 为什么：「场景动作与查看者」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。
- 性别/头型切换被旧档案回传撤销，或物品操作吞掉外观上传：[外观选择与档案回执](references/appearance-profile-sync.md)。 为什么：「外观选择与档案回执」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 装备数值改版、旧腰带强化迁移及远端动作加速，读取 [装备目录迁移与远端动作时钟](references/equipment-tuning-and-clocks.md)。 为什么：发布目标与本地历史可能变化，明确目标可避免把其他历史推到错误分支。

- 近战冲刺前踏、空中惯性、攻击 RPC 与 CMC 移动包乱序，读取 [战锤冲刺移动身份](references/hammer-sprint-movement.md)。区分隔离权威检查、实际 UDP 与最终画面覆盖。 为什么：「战锤冲刺移动身份」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

篝火食品保鲜、共享订单、F6 免食材与回执锁定，读取 [篝火食品与交易回执](references/campfire-food-transactions.md)。 为什么：「篝火食品与交易回执」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- M24 不同试装历史的部件身份、原生轴与 FX socket，以及本地 UDP 的覆盖边界：[M24 表现身份](references/m24-presentation-identity.md)。 为什么：「M24 表现身份」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 复制字段遗漏、短暂接触事件与真实 UDP 覆盖：读取[复制字段遗漏、短暂接触事件与真实 UDP 覆盖](references/replicated-terminal-events.md)。 为什么：「复制字段遗漏、短暂接触事件与真实 UDP 覆盖」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 架枪请求绑定、RPC 与属性回执交错、取消和服务器安装资格，读取 [脚架请求与确认](references/bipod-request-confirmation.md)。 为什么：「脚架请求与确认」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 进食、饮水与药水的客机取消、最早结算点和迟到回执见[消耗品结算回执](references/consumable-contact-receipts.md)。 为什么：「消耗品结算回执」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 狙击开火快照、远端短眩晕、枪声与 AI 听觉：读取 [狙击开火快照、远端短眩晕、枪声与 AI 听觉](references/sniper-launch-and-short-stun.md)。 为什么：发布目标与本地历史可能变化，明确目标可避免把其他历史推到错误分支。

涉及快速近战身份与实际联机检查时，读取 [快速近战身份与实际联机检查](references/quick-combat-authority.md)。 为什么：「快速近战身份与实际联机检查」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 强化台真实暂存、旋转占格与种植同版本快照乱序，读取 [强化暂存与种植快照顺序](references/enhancement-escrow-and-planting-order.md)。 为什么：工作区及索引包含其他任务成果，精确发布才能保留各自修改与提交边界。

## 环境动物受击与尸体复制

连续同状态受击、方向选择、晚到动作与客户端尸体表现，读取 [环境动物动作快照](references/wildlife-action-snapshots.md)。 为什么：「环境动物动作快照」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 动物掉落队列与离场保存

处理合批掉落、换图或正常退出时，读 [待提交动物掉落](references/pending-wildlife-loot.md)，不要只保存已生成的拾取物。 为什么：「待提交动物掉落」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 类玩家敌人的生命与结算

未知的客机受伤、迟到攻击、死亡重生、晚加入和换图清理，读取 [类玩家怪物的伤害与生命周期](references/unknown-combat-lifecycle.md)。 为什么：「类玩家怪物的伤害与生命周期」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

地图系统的私有/全队标记、个人迷雾和地牢实例边界，读取 [标记共享与个人探索](references/map-markers-and-personal-fog.md)。

丘陵生成地面、客机直达和内容版本兼容，读取 [丘陵生成地面、客机直达和内容版本兼容](references/hills-generated-ground-network.md)。

修女并发交谈、共享村庄修复、个人圣光学习和可破坏城门的晚加入恢复，读取 [村庄对话与防御联机边界](references/village-dialogue-and-defenses.md)。

丘陵夜袭软依赖、拥有者就绪确认及主机重启进度，读 [夜袭资源就绪与持久化](references/hills-night-readiness-and-progress.md)。
