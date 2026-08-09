extends RefCounted
## 玩家经济（UI 迁移线）：金币由旧版 GoldManager 迁移。
## 独立于背包/装备，main.gd 创建后注入各 NPC 面板。

signal changed(gold: int)

var gold := 5000

func get_gold() -> int:
	return gold

func add_gold(amount: int) -> bool:
	if amount <= 0:
		return false
	gold += amount
	changed.emit(gold)
	return true

func deduct_gold(amount: int) -> bool:
	if amount <= 0:
		return true
	if gold < amount:
		return false
	gold -= amount
	changed.emit(gold)
	return true
