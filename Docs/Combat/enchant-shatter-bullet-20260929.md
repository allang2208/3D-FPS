# 附魔卷轴：碎裂子弹

用户指定：史诗稀有度、后缀、适用所有枪械。子弹命中后向周围 5 米内随机一名敌人弹射一次；本发击杀敌人时改为向范围内所有敌人各弹射一颗。弹射继承本次射击 100% 伤害，弹射弹不会继续弹射。

## 数据与获得

| 项目 | 配置 |
| --- | --- |
| 卷轴 / 物品 ID | `shatterBullet` / `enchant_scroll_shatter_bullet` |
| 词缀槽 | suffix，替换同槽的汇聚、狼蛛或骷髅射手 |
| 限制 | firearm；步枪、狙击步枪、手枪、机枪、霰弹枪等枪械目录成员；排除弓、法杖、近战与工具 |
| 稀有度 | epic，沿用现有史诗配色和掉落光效 |
| 消耗 / 售价 | 800 魔法粉尘 / 4000 金（本轮按既有档位递增的初始配置） |
| 堆叠 / 外观 | 99；共用写实魔法卷轴图标和模型 |
| 掉落 | 地牢深度 8 起，权重 1，每次 1 张 |
| 效果键 | `shatterBullet: true`、`shatterRadiusM: 5`、`shatterDamageScale: 1` |

## 战斗口径

- 仅射出的枪械子弹命中存活敌人时触发；枪托近战、法术、箭、墙面、尸体和友方不触发。原命中被防御或状态减为零时仍可弹射，伤害继承使用防御结算前的数值。
- 以原命中点为中心查询 500 cm 球体，候选敌人的 Actor 位置须在范围内；排除原目标、射手、玩家、友方、同伴、死亡或不可伤害对象。范围内多组件按 Actor 去重。
- 沿用墙体遮挡；角色身体不阻断群体分发。非击杀均匀随机选一名；击杀为每名符合条件的敌人各生成一颗，不额外设置人数上限。无其他目标时不生成。
- 击杀由原伤害直接结算后立即记录，先于附带状态与后续火甲伤害，避免把后续效果击杀当作本颗子弹击杀。
- 100% 使用该次原命中的 `BeforeDefense` 四通道伤害，包含原射程衰减、暴击与要害倍率，不使用已被第一个敌人防御减免或被剩余生命截断的伤害。新敌人按自身防御与原穿透属性结算一次；不再随机暴击、叠加要害倍率或进行第二段距离衰减。
- 弹射产生实际飞行子弹，继承原弹速（瞬发枪无弹速时使用 500 m/s），从命中点朝选择时的敌人位置飞行；射程上限 5 米，有墙体碰撞，目标死亡后取消。不额外扣弹，不增加扳机射击次数。
- 每颗弹射弹只对应一名选中敌人，其他角色不承接该颗伤害；弹射弹不穿透目标、不再弹射。它仍走共用伤害、弹药状态、命中反馈、击杀奖励与武器修炼路径。
- 2026-09-30 按用户选定的「紫晶碎裂」接入独立弹射轨迹、起点裂闪及末端晶屑；沿用原表面/血液命中反馈。设计与接入记录见 `../Weapons/shatter-bullet-vfx-reference-20260930.md`。
- 一次射击快照保存词缀参数、伤害构成、弹速和弹道/特效来源，后续切枪或改变装备不会让飞行弹改用新枪的附魔。
- 新弹先进入 `PendingShatterRounds`，当前弹丸循环结束后再加入活动数组，下一帧开始模拟；不在持有原数组引用时递归 `Launch`。

## 接入位置

- `Content/ColdSteelData/{enhancement,items,dungeon_loot,tooltip-reference}.json`：卷轴、物品、掉落、提示定义。
- `Skills/ColdSteelSkillTypes.h`、`ColdSteelSkillRules.cpp`：射击快照与共用命中后触发入口，覆盖普通飞行弹、瞬发、枪口阻挡及双持左右手。
- `Combat/WeaponDamageTypes.h`、`Skills/ColdSteelSkillModel.cpp`：直接击杀回执与弹射伤害继承。
- `Weapons/FPSBallisticsComponent.*`、`FPSBallisticsShatter.cpp`：球形选敌、随机/群体分发、独立排队、真实弹丸及禁止再弹射。
- `UI/ColdSteelEnhancementSystem.cpp`：枪械限制排除非枪械目录。
- `UI/ColdSteelItemTooltipData.cpp`：附魔武器显示半径、随机/击杀分支、伤害倍率与一次弹射限制；附魔台沿用卷轴说明。
- `UI/ColdSteelPickupConsumable.cpp`：按 `enchant_scroll_` 家族选择已有卷轴模型，新卷轴可实际掉落和拾取。
- 附魔交易继续保存 `_enchantData` 和 `_enchantEffects`；沿用原库存、仓库与装备保存事务，不更改存档格式。

## 交付状态

首轮玩法源码与数据已落盘，以下是 2026-09-29 的玩法构建记录。2026-09-30 已另行接入并保存紫晶碎裂专属材质和原创晶片，最新 Editor/Game 构建记录见 `../Weapons/shatter-bullet-vfx-reference-20260930.md`。

- Game 构建成功：`Saved/BuildEditor/build-game-shatter-bullet-20260929.log`，`FPSGAME.exe` 已更新。
- Editor 构建成功：`Saved/BuildEditor/build-20260929-234956.log`，基础 `UnrealEditor-FPSGAME.dll` 已更新。构建后未自动打开或重启编辑器。

按用户规则未启动游戏、PIE、截图、自动化测试或运行验收，最终行为由用户测试。实现沿用现有单人战斗架构，不新增联机弹丸复制。
