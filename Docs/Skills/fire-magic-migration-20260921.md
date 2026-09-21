# 陨星坠落与灼锋焰甲迁移 · 2026-09-21

目标工程 `D:/FPS3D/FPSGAME`。源为 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev` 的 `data/skills.json`、`meteor-system.js`、`flame-armor-system.js`、`meteor-strike.js`、`flame-armor-fx.js`、`skill-manager.js`。沿用原版最终代码：陨星取消预警红圈、眩晕替代击退、火场无油面；焰甲只对非魔法攻击附伤，光环每 0.5 秒伤害。

后续表现已按 [V2 优化计划与实施](fire-magic-polish-plan-20260921.md) 更新：图标改六边形，焰甲改凝聚手势和火炬喷流，陨星使用 `PolishV2` 岩体、尾焰与碎块。下文资产清单和共同推掌描述记录初版迁移；当前表现和恢复步骤以 V2 文档为准，玩法数值仍按本文。

用户指定：**陨星当前直接施放，预留法杖条件。** `Content/ColdSteelData/skills.json` 的 `meteor.requiresStaff=false`；改为 true 后使用现有 `weaponType=staff` 判定，未虚构已经完成的法杖装备系统。

## 数据和玩法

以下 K 为 1–20 级，M 为施法时魔攻，I 为智力，最终伤害向下取整。成长整数项使用 `floor((K-1)*growth/19)`。原空间单位统一乘 1.5 转厘米。装备魔法词条、魔杖乘数、连锁/施法迅捷接口沿用已有模型。

| 参数 | 陨星坠落 | 灼锋焰甲 |
|---|---|---|
| 爆炸 / 武器附伤 | 120+12K+M(2.2+0.4K)+I(2.4+0.45K) | 10+2.5K+(M+I)(0.35+0.06K) |
| 火场 / 光环每跳 | 8+3K+(M+I)(0.25+0.03K) | 5+2K+(M+I)(0.12+0.03K) |
| 蓝耗 | 100→150 | 40→80 |
| 基础冷却 | 32→28 秒 | 60 秒 |
| 持续时间 | 3→6 秒 | 12→30 秒 |
| 爆炸半径 | (140+5K)×1.5 cm | — |
| 火场 / 光环半径 | (120+4K)×1.5 cm | (130+6K)×1.5 cm |
| 频率 | 0.5 秒 | 0.5 秒 |
| 命中 / 击杀 XP | 2 / 10 | 1 / 8 |
| 多目标 / 多杀额外 XP | 8 / 10 | 5 / 10 |

陨星射程 9.75 m，陨落 0.65 秒，爆炸伤害由中心 100% 衰减至边缘 50%。爆炸眩晕 2 秒并施加 3 层 / 3.5 秒灼烧（每层魔攻×0.5）；火场每跳再施加 1 层 / 2.5 秒灼烧（每层魔攻×0.3）。灼烧接入现有状态组件，每 0.5 秒跳伤。三维适配使用准星落点、地面法线、近似同层筛选和视线遮挡；室内从顶板下落，地面/顶板射线忽略人物身体。

焰甲附伤挂接 `ApplySkillWeaponHit` 的有效、未击杀目标。追加伤害是独立 `UFireMagicDamage`，清除武器命中修炼上下文，避免重复归为武器精通击杀，也不会由魔法再次触发。附伤与光环共用施法快照。焰甲名称不表示额外防御值，原版也未赋予该数值。

实际起手一次扣蓝并开始冷却，排队不扣费，左手长期占用直接提示。使用现有 1 秒推掌手势，服从动作互斥；法杖施法速度接口保留。接触帧重新确认落点可见且在射程内。取消不返还已提交成本。菜单取消未释放请求，已落地火场及焰甲按自身时钟继续；暂停随世界暂停。死亡、退出、切场景清理活动效果。

整次火场 / 焰甲结束后统一提交技能与暴击修炼；角色击杀经验即时结算。多目标奖励以某次爆炸或某一轮光环命中至少两名可修炼目标为条件，每次施法最多一次；多杀按整次累加。空放、尸体、友方、召唤物和 NoSkillTraining 目标不提供修炼；灼烧 DoT 不追加本技能 XP。每级升级需求 100×当前等级，20 级封顶。死亡或切场景不提交未结束的技能修炼。

存档技能版本 15→16：补入 meteor / flameArmor，新增各自剩余冷却与提交时总冷却，不修改旧进度或快捷栏。活动火场和焰甲为临时状态，不跨读档恢复。

## UI 接入规划与实现

复用 `ColdSteelSkillPage` 的 UUserWidget + Slate 页面。新卡片放在“全部 / 主动 / 魔法”，使用现有固定标题、分类、返回和可滚动正文，48px 图标与紧凑宽度合同不变。定义、当前/下级数值、经验来源均取状态模型；名称、标签、描述、修炼奖励与真实规则一致。

拖动卡片绑定现有 Q/E/X/1–4 七槽，沿用交换、解绑、保存和 E 交互优先级。快捷槽显示资源不足、排队、左手占用提示和冷却遮罩；焰甲右下数量位显示剩余秒数。图标失败保留原快捷槽回退；返回详情恢复新卡片焦点；释放 Slate 时释放新按钮。UI 不直接扣蓝或结算伤害。

新图标由 imagegen 制作银框、石墨暗底与火红主体，源在 `SourceAssets/FireMagic20260921`，运行 PNG 在 `Content/ColdSteelData/Skills`，恢复清单加入 `Tools/UI/prepare_cold_steel_skill_icons.py`。

## 特效及资产恢复

新资产目录 `/Game/Skills/FireMagic20260921`：

- `SM_MeteorRock`：本机 EasyBuildingSystem 岩石的独立副本。`M_MeteorRock` 为粗糙暗色壳层、发光熔裂纹，不依赖火苗撑起主体。
- `NS_MeteorFire`：青铜火把流动侵蚀火焰包覆岩体，火焰朝上且不随岩体自旋。
- `NS_MeteorLava`：随机圆盘火苗，`User.Radius` / `User.Fade`，末尾平滑消退；无不透明红色地面圆片。
- `NS_FlameArmorAura`：脚边小火环，显示半径贴近胶囊，实际伤害半径使用技能数据。
- `NS_FlameArmorWeapon`：沿真实刀刃端点 / 枪口短段的附焰；`User.WeaponEnd` 为世界朝向的局部偏移，`User.Fade` 控制末尾消退。
- `NS_FireMagicSparks`：现有火球一次性火星发射器副本，命中短促四散。
- `S_FireMagicCast` / `S_MeteorLand` / `S_MeteorBurn` / `ATT_FireMagic`：原项目火球起手、陨星落地及循环燃烧音频，48kHz 单声道，场景距离衰减。

复用当前 `/Game/Skills/Fireball/NS_FireballVelocityTrail`、`ImpactRealistic20260914/NS_FireballImpactRealistic` 与 `M_FireballHeatShockwave`；不修改火球母版。落地短震通过角色原有镜头表现叠加口径，遵循 `fps.Camera.Shake`。

先运行 `Tools/Skills/prepare_fire_magic_sources.py` 准备本机原始音频和生成图；已有派生源直接恢复即可。通过项目 MCP 桥在编辑器内 `importlib.reload(build_fire_magic_assets)` 后依次 `run('materials')`、`audio`、`meteor`、`lava`、`armor_aura`、`armor_weapon`、`sparks`。每阶段保存独立资产与本地制作记录。保留 Vefects、Niagara Examples、EasyBuildingSystem 和火把依赖；本机已持有不表示可公开再分发，原包二进制与音频保留本机许可边界。

## 交付状态

作者阶段已完成并保存；Niagara / 材质必要编译由制作脚本执行。普通 FPSGAMEEditor Development 构建返回 Succeeded（等待已有构建后，UBT 返回 Target is up to date）。新增类通过普通基础模块加载，不依赖 Live Coding 补丁。

**按用户规则未启动 PIE、未运行测试、未截图或渲染验收。实际玩法、伤害、存档与视觉表现交由用户测试。**
