extends RefCounted
## Buff/状态效果数据库（旧版 status-bar.js STATUS_CONFIG + damageable-entity.js 全量移植）
## 描述/图标/配色与旧版一致；机制字段（tick 间隔等）供 buff_system.gd 消费。

const DEFS := {
	"stun": { "icon": "💫", "name": "眩晕", "color": "#9a7a5a", "desc": "无法移动、攻击、使用技能与物品。" },
	"poison": { "icon": "☠️", "name": "中毒", "color": "#7a9a5a", "desc": "每秒受到层数点毒素伤害。", "tick_ms": 1000 },
	"slow": { "icon": "🐌", "name": "减速", "color": "#5a7a9a", "desc": "移动速度降低 50%。" },
	"bind": { "icon": "⛓️", "name": "束缚", "color": "#7a5a8a", "desc": "无法移动，可攻击施法。" },
	"buff": { "icon": "✨", "name": "增益", "color": "#9a9a5a", "desc": "获得临时增益效果。" },
	"shield": { "icon": "🛡️", "name": "护盾", "color": "#5a8a9a", "desc": "获得护盾，减免受到的伤害。" },
	"bleed": { "icon": "🩸", "name": "流血", "color": "#9a3a3a", "desc": "每层每秒流失当前生命 1%，持续 10 秒。", "tick_ms": 1000 },
	"inspire": { "icon": "📣", "name": "激励", "color": "#ffb347", "desc": "移动速度 ×1.33、物理攻击 ×1.5（怪物增益）。" },
	"magicVulnerability": { "icon": "🔮", "name": "魔力易伤", "color": "#8a5a9a", "desc": "每层使受到的魔法伤害提高 5%。", "stacks_mult": 0.05 },
	"droneVulnerability": { "icon": "🛸", "name": "无人机易伤", "color": "#5a7a9a", "desc": "每层使受到的所有伤害提高 10%。", "stacks_mult": 0.10 },
	"fear": { "icon": "😱", "name": "恐惧", "color": "#7a5ac8", "desc": "失控地远离恐惧源，每层移速再降 33%（上限 99%）。" },
	"statusImmune": { "icon": "🔰", "name": "状态免疫", "color": "#5ac8c8", "desc": "免疫一切其他状态效果。" },
	"haste": { "icon": "💨", "name": "加速", "color": "#5ac85a", "desc": "每层移动速度 +10%。", "per_stack": 0.10 },
	"holyRenewal": { "icon": "💚", "name": "圣光续疗", "color": "#7aff9a", "desc": "每秒恢复最大生命值 1%×层数 的生命值。", "tick_ms": 1000, "heal_percent": 0.01 },
	"marbleHeal": { "icon": "🗿", "name": "大理石守护", "color": "#8a9a8a", "desc": "击杀目标后 1 秒内回复生命值。" },
	"goddessBless": { "icon": "✨", "name": "女神祝福", "color": "#e8c878", "desc": "本场战斗攻击/防御/移速提升，按场消耗。" },
	"demonPrayer": { "icon": "🔥", "name": "恶魔祈祷", "color": "#9a3a3a", "desc": "攻击力大幅提升的恶魔交易，伴随代价。" },
	"tributeSnowLotus": { "icon": "🪷", "name": "雪莲祝福", "color": "#9ad0ff", "desc": "本次地牢获得经验 +25%。" },
	"tributeGinseng": { "icon": "🌿", "name": "人参回气", "color": "#6a9a5a", "desc": "本次地牢击杀目标后 1 秒内回复最大魔法值 5%。" },
	"tributePeach": { "icon": "🍑", "name": "蟠桃续命", "color": "#e8a06a", "desc": "本次地牢死亡后 3 秒以 30% 最大生命原地复活一次。" },
	"tributeDiamond": { "icon": "💎", "name": "金刚不坏", "color": "#7ab0e0", "desc": "单次受到的伤害不超过最大生命值的 15%。" },
	"tributeMoonstone": { "icon": "🌙", "name": "月影庇护", "color": "#b0a0e0", "desc": "进入战斗获得无敌；Boss/精英战斗中物理魔法伤害 +5%。" },
	"tributePhilosopher": { "icon": "🪨", "name": "点石成金", "color": "#e0c060", "desc": "获得随机传说祭品（若为传说祭品则额外再得一份）。" },
	"chainSpell": { "icon": "🔗", "name": "链式强化", "color": "#8a7a6a", "desc": "下次施法的魔法伤害与 MP 消耗按层数提高。" },
	"chill": { "icon": "❄️", "name": "寒冷", "color": "#7ab8e0", "desc": "每层降低 5% 移动速度；叠满 20 层触发冻结。", "stacks_mult": 0.05, "freeze_at": 20, "freeze_cost": 10 },
	"burn": { "icon": "🔥", "name": "灼伤", "color": "#ff6b35", "desc": "每 0.5 秒受到施法者魔法攻击×0.5 的魔法伤害。", "tick_ms": 500, "damage_mul": 0.5 },
	"frozen": { "icon": "🧊", "name": "冻结", "color": "#a0d8ff", "desc": "无法移动、攻击、使用技能与物品；受到的非魔法伤害提高 50%。", "physical_bonus": 0.5 },
	"flameArmor": { "icon": "🔥", "name": "灼锋焰甲", "color": "#ff7a3a", "desc": "攻击附带魔法伤害并迸发火花；每 0.5 秒灼烧周围敌人。" },
	"electrified": { "icon": "⚡", "name": "感电", "color": "#b98cff", "desc": "每层使受到的电系伤害提高 3%；叠满 5 层触发过载：眩晕并释放电弧传导。", "stacks_mult": 0.03, "overload_at": 5 },
}

static func get_def(type: String) -> Dictionary:
	return DEFS.get(type, { "icon": "❓", "name": type, "color": "#8a7d6b", "desc": "持续生效的状态效果。" })
