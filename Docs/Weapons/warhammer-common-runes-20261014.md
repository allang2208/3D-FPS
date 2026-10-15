# 战锤复用剑类通用符文

战锤 `rune` 栏复用 `melee-gunsmith.json` 的 `blade_2` 列，保持 `haste_rune`、`resonance_rune`、`erosion_rune`、`conduction_rune` 四个通用 ID。读取现有选项的名称、属性、说明和特效；不另存一套数值。寒晶精神迸发、金色强化、蛮荒、祥云、山岳以及传说符文不进入战锤目录。

| 通用符文 | 沿用的效果 |
| --- | --- |
| 急速 | 攻击速度 +10% |
| 共鸣 | 持握时所有技能冷却 -15%，使用技能时确定冷却 |
| 侵蚀 | 战锤攻击附加「智力×10%＋精神×10%」魔法伤害，随攻击倍率结算 |
| 导魔 | 持握时魔法伤害 +15%；战锤攻击命中使目标受到的魔法伤害提高 10%，持续 10 秒，重复命中刷新 |

## 目录与展示

`warhammer-gunsmith.json` 的 `rune.options_library` 指向 `melee-gunsmith.json`，`options_column` 为 `blade_2`。`WarhammerGunsmith.cpp` 从来源列选取四个通用 ID，读取所有技能冷却、魔法冷却、魔法伤害、侵蚀系数及导魔易伤字段。允许列表由 `ColdSteelFrostRunes::IsCommon` 共用，归一化及外观入口也遵守此列表；剑类原有兼容名单继续由剑类目录使用，侵蚀在寒晶上的原生／专属语义不变。

加载战锤文案时把剑刃相关部位词替换成锤身、战锤攻击，去除剑类独有的旋风攻击枚举，不改原目录的数值。工作台详情、总览和物品浮窗增加实际魔法倍率与易伤显示；侵蚀仅说明属性转化规则，不额外展开附伤金额。

选项图标直接解析已有 `blade_2_<id>.png` 共享键，未复制或重新生成四张图。分类继续使用 `category_rune`，空槽继续使用 `rune_false`。

## 效果结算

- 共鸣改为共享 `skill_cooldown_mult: 0.85`，覆盖魔法、旋风斩、上挑及环绕飞剑，实际使用时形成冷却快照。原有魔法专属冷却倍率保留独立乘区；攻击动作／收招、被动触发间隔不按技能冷却缩短。飞剑召唤时记录倍率，结束环绕时开始计时，收起武器不会重算本次冷却。数值调整的构建状态见 [共鸣调整记录](resonance-all-skill-cooldown-20261014.md)。
- `ColdSteelMelee::EquippedModifiers` 读取当前真正持有的双手剑或双手钝器，使既有法术伤害和冷却评估能够读取战锤符文；持握采集工具时仍不借用收起的剑。
- 侵蚀与魔法增伤沿用 `WeaponDamagePanel` 和 `ColdSteelTool::Evaluate`，先形成物理／魔法伤害快照，再由攻击阶段倍率缩放并按对应防御结算。
- `ColdSteelSkills::Snapshot` 将战锤导魔易伤比例和时长写入本次出手快照。普通连击、重击与冲刺砸地使用同一快照；重击／冲刺冲击波携带已提交的快照。
- `ColdSteelSkillModel` 在有效的权威战锤命中结算后施加魔法易伤；排除死亡目标、友方和跳弹。每个目标沿原有命中去重流程结算，重复命中刷新时长，当前这一击不提前吃到新施加的易伤。
- 未附带剑类自带的命中减冷却机制，也没有新增专属符文效果。锤头、锤座的既有倍率继续与符文倍率相乘。

## 表面与资源

用户随后要求将符文移到裸露金属柄，并避免缩小及过度拉伸。当前修改将承载部件改为固定 `shaft` 模块，武器坐标 Z=42.5 至 80 cm，长度 37.5 cm；按表面弧长和源纹理宽高比建立等比例展开。共鸣宽纹样环绕一周，较窄的完整纹样分置相对两面，两端与套箍、包覆保持间距。颜色、明灭、流光、属性和改造图标保持原有规则。

新材质路径为 `/Game/Weapons/SteelWarhammer20261014/Runes/ShaftWrapV2/M_SilverRuneSurface_WarhammerShaftV2`。装配入口清除中央锤座的旧覆盖，并只向金属柄应用新材质。旧 `/Game/Weapons/SteelWarhammer20261014/Runes/M_SilverRuneSurface_Warhammer` 保留为来源资产；其中央锤座 7.5×8.6 cm 平面投射是上一版记录。新版本的实际保存与构建结果见 [ShaftWrapV2 制作记录](../../SourceAssets/WarhammerCommonRunes20261014/ShaftWrapV2/README.md)。

柄面环绕版本已后台保存，commandlet 返回 0，Game 与 Editor 构建均返回 `Succeeded`；Editor 为共享构建结束后的当前目标最新状态。未主动打开编辑器、运行游戏或制作验收截图。

共享模块装配读取战锤的 `rune` 槽，切换签名包含该选择；资源沿现有异步收集加载，清除符文恢复无覆盖材质。无需新增轮询或逐帧读取目录。持握、改造草稿、掉落与装备捕获继续使用相同装配入口。

作者目录 `SourceAssets/WarhammerCommonRunes20261014/` 保留注册入口、实际源着色器快照、战锤投射代码、最终材质代码与资产导入回执。当前柄面环绕制作入口位于其 `ShaftWrapV2/` 子目录。旧 `WarhammerRuneSlot20261014` 的空槽制作记录为前一阶段。

本轮进行必要的后台材质保存和 Editor／Game 构建，不主动打开编辑器或运行游戏、截图、UI／联机测试。资产保存、原生构建和用户实机体验分别记录。

初次通用符文接入状态（本次数值调整前）：战锤符文材质保存完成，四种通用选项已引用正式目录。Editor 与 Game 目标均取得 UBT `Succeeded` 结果，完整结果副本保存在作者目录的 `shared-editor-build-receipt.log` 与 `shared-game-build-receipt.log`，`build_status.json` 区分日志来源。本次共鸣调整的构建状态单独记录。

本任务首次 Editor 构建遇到其他并行修改的 `M66IncineratorMonster.h` 与旧生成代码不同步；未修改或回退该怪物源码。等待已有构建完成后读取当前共享目标的成功结果，没有重复抢占 UBT 或联系其他任务。源码构建和资产保存完成不代表游戏内显示、命中效果或联机已测试。
