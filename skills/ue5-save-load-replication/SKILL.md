---
name: ue5-save-load-replication
description: UE5 save/load and replication workflow for persistent state, server authority, RPCs and reconnect or travel recovery.
---

# 联机存档与恢复

本机维护源：[ue5-save-load-replication](C:/Users/allan/.codex/skills/ue5-save-load-replication/SKILL.md)。遵守工程 AGENTS.md、WORKFLOW.md 和本次用户授权，不自动启动编辑器或测试。

FPSGAME 主客机归属、事务中断、重连／重生／换图、工作站恢复及覆盖记录，读取 [生命周期与覆盖记录](../ue5-cpp-gameplay/references/multiplayer-lifecycle-and-coverage.md)。该参考可跨机器读取；历史构建不代表当前运行验收。

## 持续技能的保存顺序

FPSGAME 持续魔法的施法身份、预测确认、权威奖励模型及断线／换图先结算后保存，读取 [持续魔法的联机状态与收尾](../ue5-skill-magic-workflow/references/persistent-magic-network.md)。

区域首领目标、允许队友入场的方向闸门及每位玩家的区域追踪，读 [区域首领联机规则](references/regional-boss-objectives.md)。

物品占格改变、旧地面物品、客机重连与共享容器旧键迁移，读取 [占格迁移覆盖](references/inventory-footprint-migrations.md)。

装备符文的远端材质、攻击耗体与武技冷却确认，读取 [装备符文与攻击提交回执](references/equipment-runes-and-attack-receipts.md)。

## 近战防御动作的网络身份

复用剑/工具格挡、旧轮次回执、攻击互斥、客机中断与复制破防，读取 [近战格挡轮次](references/melee-guard-intent.md)。
