---
name: ue5-save-load-replication
description: UE5 save/load and replication workflow for persistent state, server authority, RPCs and reconnect or travel recovery.
---

# 联机存档与恢复

焚化炉、弹药暂存、永久销毁确认及晚到回执／重连绑定清理，读取 [永久销毁与暂存恢复](references/destructive-inventory-and-escrow.md)。

本机维护源：[ue5-save-load-replication](C:/Users/allan/.codex/skills/ue5-save-load-replication/SKILL.md)。遵守工程 AGENTS.md、WORKFLOW.md 和本次用户授权，不自动启动编辑器或测试。

FPSGAME 主客机归属、事务中断、重连／重生／换图、工作站恢复及覆盖记录，读取 [生命周期与覆盖记录](../ue5-cpp-gameplay/references/multiplayer-lifecycle-and-coverage.md)。该参考可跨机器读取；历史构建不代表当前运行验收。

## 持续技能的保存顺序

FPSGAME 持续魔法的施法身份、预测确认、权威奖励模型及断线／换图先结算后保存，读取 [持续魔法的联机状态与收尾](../ue5-skill-magic-workflow/references/persistent-magic-network.md)。

区域首领目标、允许队友入场的方向闸门及每位玩家的区域追踪，读 [区域首领联机规则](references/regional-boss-objectives.md)。

物品占格改变、旧地面物品、客机重连与共享容器旧键迁移，读取 [占格迁移覆盖](references/inventory-footprint-migrations.md)。

装备符文的远端材质、攻击耗体与武技冷却确认，读取 [装备符文与攻击提交回执](references/equipment-runes-and-attack-receipts.md)。

## 近战防御动作的网络身份

复用剑/工具格挡、旧轮次回执、攻击互斥、客机中断与复制破防，读取 [近战格挡轮次](references/melee-guard-intent.md)。

## 第三人称武器表现

远端静止瞄准、装备／身体态乱序、机械支撑手与激光落点的身份约束，以及受控联机检查的覆盖边界，读取 [全身表现的联机瞄准与接触](../ue5-cpp-gameplay/references/player-world-body.md#联机瞄准与接触)。

- 弓换手、双手进食收弓及事件滞留的复制边界：[弓与消耗品表现同步](../ue5-cpp-gameplay/references/player-world-body.md#弓换手与消耗品恢复的表现同步2026-10-18)。

- 移动怪物延迟命中、弱点遮挡及器官生命池：读取 [monster-delayed-hit](references/monster-delayed-hit.md)。

- S12K 试装历史导致的复制清单差异与第三人称方向：[S12K 试装历史导致的复制清单差异与第三人称方向](references/saiga12k-presentation.md)。按问题读取；历史检查不授权自动重测。

## 提前准备的怪物实例

处理服务端延迟生成、激活复制、区域分路和取消清理时，读 [区域提前准备的联机边界](../ue5-performance-packaging/references/area-spawn-preparation.md#联机与延迟初始化边界)。客户端资产或 PSO 已加载不代表每实例蒙皮缓冲已经准备；构建结果与主客机运行覆盖分别交付。

- SVCH 改造历史引起远端部件编号差异，或核对近战/换弹的联机检查范围：读取 [SVCH 配件身份与联机覆盖](references/svch-presentation-coverage.md)。区分隔离权威、实际 UDP 和完整实战流程。

- 装备穿戴已更新但旧物品／共享掉落物仍显示旧版，读取[旧装备实例与外观路径](../asset-model-workflow/references/continuous-boots-and-render-lods.md#装备接入与旧实例)，保留实例属性并区分监听主机、重连及未覆盖的网络模式。

## 场景家具与表现同步

可重复开关的柜体、多人查看者生命周期、坐卧晚加入及设备/环境动画时钟，读取 [场景动作与查看者](references/scene-motion-and-viewers.md)。库存事务与表现状态分别维护；需要检查时才启用案例中的多进程夹具。

## 手枪装填与弹药对账

补弹后射击被拒、切弹种首发不一致、左轮中断或双枪共享弹池时，读 [手枪装填权威](references/pistol-ammo-authority.md)。表现复制与实际弹药结算分开核对。
- 性别/头型切换被旧档案回传撤销，或物品操作吞掉外观上传：[外观选择与档案回执](references/appearance-profile-sync.md)。

- 装备数值改版、旧腰带强化迁移及远端动作加速，读取 [装备目录迁移与远端动作时钟](references/equipment-tuning-and-clocks.md)。

- 近战冲刺前踏、空中惯性、攻击 RPC 与 CMC 移动包乱序，读取 [战锤冲刺移动身份](references/hammer-sprint-movement.md)。区分隔离权威检查、实际 UDP 与最终画面覆盖。

篝火食品保鲜、共享订单、F6 免食材与回执锁定，读取 [篝火食品与交易回执](references/campfire-food-transactions.md)。
