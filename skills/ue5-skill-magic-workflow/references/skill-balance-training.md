# 技能数值审计与修炼项接入(2026-09-17/18)

2026-09-17 全量审计 13 个技能的四层链路,2026-09-18 用户拍板经验×3 与巧手新增修炼项。本文沉淀审计方法、踩坑与修炼项接入合同,后续调数值或加修炼项先读这里。

## 四层链路与审计方法

技能数值走同一条链,审计就是逐层对表:

1. **数据**:`Content/ColdSteelData/skills.json`(唯一调参入口);
2. **加载**:`ColdSteelSkillRules.cpp` 的 `LoadDefinition`(每个字段都有 clamp 上下限);
3. **生效**:`ColdSteelSkillModel.cpp` / `ColdSteel*Model.cpp` / `UI/ColdSteelProfileRuntime.cpp`(`FireballStats`/`IceSpikeStats`/`QuickCombatStats` 等);
4. **面板**:`UI/ColdSteelSkillPage.cpp`(收益行、修炼卡)与 `EffectSummary` 升级提示。

审计结论:四层读同一函数,不存在"显示一套、生效另一套";修复只删不改语义。

## 踩坑记录

- **JSON 里的 `maxLevel` 是死字段**:`LoadDefinition` 从不读取,20 级上限硬编码在 `ColdSteelSkillTypes.h` 默认值 + `Validate` 的 `Level>20` 校验。改 JSON 的 maxLevel 无效,改大了反而以"技能等级无效"拒档。已从 JSON 删除全部 13 处(schemaVersion 8→9)。要改上限必须同步改默认值与 `Validate`。
- **加载但无消费者的字段 = 死数据**:机枪 `spreadDelayPerLevel`、散弹 `knockbackPerLevel` 装载后没有任何战斗代码消费,面板也不显示——数值上"成长了"实际无效。已连同 `FColdSteelSkillEffect.SpreadDelay/Knockback` 整体删除。加新成长字段前先确认生效侧有消费者。
- **负向表述会被读反**:剑/弓精通的攻速机制是攻击速率 ÷(1−缩减)(`MeleeWeaponStats.cpp`),等级越高出手越快;但面板写"攻击间隔缩减 −X%"被用户误读为"减攻速"。已改为正向"攻击速度 +X%",换算 `1/(1−缩减)−1`。新面板行优先写玩家视角的正向收益。
- **提交树可能扫入半成品**:并行会话的大提交曾把只改了一半的 `ColdSteelProfileRuntime.cpp`(引用 `MeleeKillExperience`)扫进 a34d6cc,而定义侧未进——HEAD 编译不过,工作区是全的。遇到"干净树编不过"先对照工作区补齐定义侧,别回退。

## 修炼项接入合同(2026-09-18 已落地的巧手案例)

新修炼项四步:

1. **数值字段**:`skills.json` 加 `xxxExperience`(默认 0 不影响其他技能),`LoadDefinition` 加 clamp 读取,`ColdSteelSkillTypes.h` 加字段;
2. **快照标记**:能挂在既有命中/击杀事务上的(近战命中/击杀),在 `Snapshot` 里打标(`FColdSteelSkillShot.bMelee` 按 `IsMeleeWeapon`),`ApplySkillWeaponHit` 命中侧与 `AwardKill` 击杀侧各自结算——击杀档"含命中"合计发放,口径同暴击包;
3. **独立动作**用 `TrainDexterousHands`(通用入口,已预留):一次性行为的钩子调用它;
4. **面板同步**:`ColdSteelSkillPage.cpp` 修炼卡加行(经验为 0 的行自动隐藏),描述文案更新。

**修炼项候选评估标准**(2026-09-18 用户裁定,先于实现):

- **防刷**:可原地无脑重复的动作不合格——"翻越/攀爬"因能原地反复爬被剔除;"使用消耗品"因属资源行为且不合巧手主题被剔除。合格项要么要求可修炼的活体目标(近战命中/击杀,沿用 Summoned/NoSkillTraining/尸体排除),要么有自然频率限制(换弹需实际补入弹药)。
- **主题契合**:修炼项必须是该技能身份的自然延伸,不凑数。

## 平衡口径(2026-09-18 生效)

- 全技能 `experiencePerLevel` 100→**300**,满级 19,000→**57,000**,所有用时 ×3。
- 产速差距由修炼通道决定:魔法多目标奖(达标固定制)在刷怪群收益无上限,火球清群仍最快;"多目标奖按超额人数递减"方案(见 `Docs/SkillTrainingBalance20260917.md` 方案 B)待实测后再定。
- 满级用时测算法:按强度分档(高强度 ≈15 杀/分钟、60% 暴击;魔法 12 秒冷却满转),修炼值产出 ×6 折算时产;各技能完整测算表在 `Docs/SkillTrainingBalance20260917.md`。

## 遗留口径(调参时顺手定夺,非缺陷)

- 火球半径公式用 `L` 而非 `L−1`(`ColdSteelFireballModel.cpp`),1 级已含首级增量,与蓝耗/倍率基线不一致;
- 火球有 8s 冷却硬地板但符文倍率在其后可击穿;冰锥无地板——面板"常规最低冷却"恒显 8.0s;
- `costReductionPerLevel` clamp 上限 4.5%/级,20 级闪避只花 10% 体力,JSON 调参别顶到上限。
