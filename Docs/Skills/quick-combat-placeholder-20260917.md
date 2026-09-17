# 快速进战技能接入（2026-09-17）

## 需求与范围

- 占位接入：新增技能「快速进战」，触发快捷键 F；原 F 键的武器检视改绑 L（第二轮已按 UI 分卷规则补齐卡片与拖动绑定）。
- 正式效果（同日用户定义）：对前方 2m 的单个单位造成伤害，伤害 = 25 + 技能等级×5 + 力量×（5 + 技能等级×0.1）（同日二次调整，初版 50 + 等级×10 被用户判定过高），击退 1m 并眩晕（2.5 + 技能等级×0.1）秒。按 F 且装备剑类武器时触发，动作取第四连击的配重锤打击；其他武器版本后续设计。

## 数值与公式口径

- 公式按用户原文「×技能等级」字面结算（伤害项 2026-09-17 二次下调为 25+5×等级）：1 级基础 30 伤害 / 2.6 秒眩晕，20 级基础 125 伤害 / 4.5 秒眩晕（力量项另计）。
- 力量取 `UColdSteelStatusModel::Attribute("str")` 当前总值（基础属性 + 装备 + 重击/机枪精通的力量加成合并）。
- 参数入口统一在 `Content/ColdSteelData/skills.json` 的 `quickCombat`：`damageBase/damagePerLevel/strengthFactorBase/strengthFactorPerLevel/knockbackCM/rangeCM/stunBase/stunPerLevel/cooldown`。

## 冷却（基础 12 秒，2026-09-17 第二次补充）

- 完全沿用火球/冰锥的「预留-结束起跳」合同：动作实际开始时 `CommitQuickCombatCast` 预留全额冷却（`bQuickCombatReserved`，预留期间不走表）；挥击结束 `FinishQuickCombatCast` 解除预留后 12 秒才开始走表；取消（死亡/换装/不可用走 `CancelAction`）与存档重载（abandoned 清理）同样解除预留并**保留**已提交的冷却。
- 门禁：`TriggerQuickCombat` 在 reserved 或剩余冷却 >0 时拒绝；开发面板「无能力冷却」调项照常生效。
- 存档字段 `QuickCombatCooldown/Duration/bQuickCombatReserved` 并入版本 11 合同（该版本今天才引入，未发布，无需再 bump）；`Validate` 校验有限性、时长 ≥ 剩余、≤300。
- 快捷槽接入冷却遮罩与数字读秒（`ColdSteelQuickSlot` quickCombat 分支）。

## 修炼（参考其他技能定值，2026-09-17 第二次补充）

- 释放技能 +1（`useExperience`，动作实际开始记，挥空也算；排队补发算一次）——对齐重击/闪避的使用口径。
- 使用技能击杀目标 +15（`killExperience`）：可修炼目标（有 MonsterCombatComponent、非尸体、非召唤/NoSkillTraining）被本次打击直接击杀时，挥击结束统一提交。参考系：冰锥每杀 12、重击首档（同次 2 杀）12、火球每杀 24；本技能为 12s 冷却的单目标必中打击+硬控，取 15 居中。
- 无命中/多目标档（单目标技能）；命中继续按剑类命中修炼剑精通与暴击（既有快照路径）。

## 已接入内容

- **数据与存档**：skills.json 正式数值；存档版本 10→11 自动补键；`FQuickCombatTuning`（ColdSteelSkillTypes.h）由 `ColdSteelSkills::LoadDefinition` 解析。
- **触发链**：F（`QuickCombat` ActionMapping）或快捷栏绑定 → `UColdSteelStatusModel::TriggerQuickCombat` → 限剑类（当前符文剑 `IsEquipped`）→ `URuneSwordComponent::BeginQuickCombatStrike`。
- **动作**：复用第四连击的 `PommelStrike` 剪辑与全部节奏/镜头/音效/ rift 表现（`bPommelAttack` 路径，天然单目标、前方窄走廊）。不推进普通连击计数（直接调 `StartSwing`，不经过 `BeginAttack`）。守卫/装备/收手等占用与普通攻击一致；施法占用左手时拒绝；挥击接触段结束后按 F 排队补一记（`bQueuedQuickCombat`，挥击结束处消费）。消耗一次普通攻击体力（沿用 `StartSwing` 既有扣减，与重击同口径）。
- **结算**：命中后 `SwingDamage` = 技能公式结果，经既有 `ColdSteelSkills::ApplyHit` 面板管线（同重击：金额按武器伤害面板比例分摊）；命中即 `UMonsterCombatComponent::ReceiveStun(Pawn, StunSeconds, 100cm)` 一次提交击退+眩晕，普通推退在该打击内关闭。范围 `SwingReach = max(武器 reach, 200cm)`。
- **眩晕**：新增 `ReceiveStun`（MonsterMeleeKnockback.cpp），镜像格挡反制流程（打断攻击 → Stagger 状态 → BeginReaction 控制闸 → 停止移动 → 立即推 20% + 0.16s 内推余下 80%），不带招架表现标记。覆盖 Wolf/Maggot/Nurse/HandBrain 四类 AI 怪；FatZombie/Mutant3 走独立 FPSCombatHealthComponent，与格挡/击退一致不受此组件管。
- **修炼**：动作实际开始时记 useExperience=1（挥空也算施放；排队补发算一次）；命中经既有快照继续修炼剑精通与暴击。升级提示由 `QueueProgressNotices` 自动发布（Detail 显示新等级打击伤害与眩晕秒数）。
- **UI**：技能页详情换正式效果行（触发键 F / 打击伤害含当前力量 / 力量系数 / 眩晕时间 / 击退距离，当前/下一级对照）；标签「剑技 / 打击 / 主动」；快捷栏拖动绑定保留。开发面板可升/满级。
- **图标**：1254×1254 六边银框系列占位图（以暴击图为基底，仅换中央双箭头符号），`SourceAssets/QuickCombat20260917/`，恢复脚本已登记。正式图标后续按同规则重制。

## 决策点（可再调）

- 体力：用户未指定，暂按近战动作合同消耗一次普通攻击体力；如需无消耗，改 `StartQuickCombatStrike` 即可。
- 公式字面按 ×等级（伤害项现为 25+5×等级，1 级基础 30 伤）；若再调公式只改 `QuickCombatStats` 与 skills.json 的 damageBase/damagePerLevel。
- 连发由 12 秒冷却与动作节奏限制；冷却中按键无效（快捷槽显示读秒遮罩）。

## 交付前自查修正（2026-09-17 第三轮）

- 快捷槽可用性变暗极性写反（原 `Dim=!Fraction` 会在就绪时变暗）：改为「无剑或冷却中才变暗」，并在未装备剑类时显示「需剑类」而非读秒。
- `EndPlay` 补冷却预留释放（与 `FinishHeavyTraining` 同口径），避免销毁路径把预留标志留给下次会话；存档加载的 abandoned 清理仍作为兜底。
- `StartSwing` 防御性复位 `bQuickCombatStrike`，确保任何进入普通挥击的路径都不会残留技能标记。
- `Migrate` 清理上一轮留下的不可达行（`P.SkillProgressVersion=10`）。
- 交叉核对 skills.json 键名与 `LoadDefinition` 解析键（damageBase/damagePerLevel/strengthFactorBase/strengthFactorPerLevel/knockbackCM/rangeCM/stunBase/stunPerLevel/cooldown/killExperience）逐项一致。

## 快捷栏 F 专属槽（2026-09-17 第三次补充）

底部快捷栏在数字 1–4 组后用同一细分隔线隔开，追加一枚 **F 固定槽**：与七槽混放槽共用 `UColdSteelQuickSlot`（同尺寸、同框、同图标路径、同冷却遮罩/读秒/就绪白光/键位呼吸闪动），格式完全统一。

- 槽位新增「固定技能模式」：`Configure(Owner, Index, FixedSkill)` 传入 `quickCombat` 后只读显示该技能——不读混放绑定、不可拖出、不收投放（四处拖放入口 + `NativeOnDrop/DragOver` 全部早退）；键位标注给定为 F。
- HUD 侧刻意**不**把该槽注册进 `QuickSlotSurfaces`（`QuickBarDropIndex`/`HighlightQuickBar` 遍历它解析投放目标）也不进 `HotbarDropSlots`，拖动高亮与投放不会落到它上；`RefreshQuickBar` 的 0.05s 轮询仍覆盖它，冷却读秒/遮罩持续刷新。
- 槽内状态沿用既有语义：无剑类装备时变暗并显示「需剑类」；冷却中显示数字读秒 + 黑色遮罩；冷却结束触发就绪白光。悬停提示「F · 快速进战 / 按 F 直接触发；冷却结束后可用」。

## 手枪版握把砸击（2026-09-17 第四次补充）

单持手枪按 F：松开左手、右手单独持枪、以**握把部分向前猛砸**。动作按 [施法与完整骨段](../../skills/ue5-fps-arms-animation/references/casting-arm-volume.md) 与 [手枪动作适配](../../skills/ue5-fps-arms-animation/references/pistol-adaptation.md) 的既定路线做**程序化姿态层**（火球 V3 同一机制家族），不做 FBX 烘焙。

- **节奏分段**（`QuickCombatPistolMotion.h`，对齐配重锤的起势—接触—收势）：松左手 0–0.16s → 右手上抬竖枪 0.16–0.40s（握把底甩向目标，枪口上仰 38°）→ 前砸 0.40–0.58s（接触点 0.54s，回正到 12°）→ 收势 0.58–1.02s（左手回握闭指）。全部目标相对入场快照，适配任意待机姿态。
- **姿态层**：`FPSCastingMeshComponent::ApplyQuickCombatPose` ——双臂两骨 IK（恒骨长、93% 肩带支撑、前臂继承掌侧 roll 的闭式解，与火球/符文剑同一修复）；左手手指张开度借用火球手型配置与逐指延迟曲线；锁骨保持动画驱动；右手手指保持动画握持并随被接管的手腕刚体跟随；`WPN_root` 挂右手链下时自然跟随，否则按右手入场差值整组刚体搬运（骨架挂接关系运行时检测）。
- **状态机**：`UFPSQuickCombatComponent`（`FPSQuickCombatComponent.h/.cpp`）——Trigger 门禁在角色侧 `AFPSGAMECharacter::TriggerPistolQuickCombat`（单持、非 busy、非施法占用、存活）；动作实际开始提交冷却与使用修炼；接触点沿准星 2m 球形单目标结算（同剑版伤害/击退/眩晕公式，`ReceiveStun` 一次提交），可修炼目标击杀在收势统一提交 +15；收势结束冷却起跳。
- **仲裁**：砸击占用计入 `IsCastingWithLeftHand`（装备换装锁）、`IsCastBlockingLeftHandAction`（新左手工序拒绝）、`IsWeaponBusy`（ADS 自动压制）；`FirePressed` 在砸击期间不接开火；双持左手被副枪占用不触发；换枪/双持/死亡在 Tick 立即收手，冷却照常保留。
- **V1 已知边界**：无前踏步（猛砸距离感靠手臂+肩带前送，待反馈再议突进）；砸击期间普通攻击恢复后的衔接、滑动/翻越中的表现未调；双手 IK 为 V1 参数（起抬 38°、前送 +20cm），形变与手感以用户实机反馈为准（火球 V1→V3 同样迭代）。

## V2：按 COD4 UZI 近战参考重调（2026-09-17 第五次补充）

用户指出 V1 完全不合格，给出 B 站参考 BV13K421e7Rw（COD4 模组展示）45–47s 的 UZI 近战段。下载该视频逐帧看过，提炼的动作语言：

- **枪向右肩方向快速上提、枪口朝上**（不是 V1 的小幅水平后收）；
- **从高处斜向下前方一记短促前捅**，机匣尾/握把端领先——高低差是力度来源，不是水平推；
- **左手同步张开、向左前方开掌推挡**（V1 的"垂到低守位"方向就错了）；
- **全程约 0.5 秒**，干脆利落，收势极短。

据此重写 `QuickCombatPistolMotion.h`：总时长 1.02s→0.85s（接触点 0.54s→0.42s）；上抬角 38°→55° 且终点改到右肩高度（-12,+4,+9）；前捅终点改为斜下前方（+18,+2,−14，高低差 23cm）；左手从低守位改为与砸击同步的左前推掌（+6,−22,−2）。姿态层与组件逻辑不变，只换曲线常量。

参考声明：只借鉴动作语言（节奏/方向/左右手职责），COD4 动画资产有版权未提取；本实现仍为程序化原创。V2 待实机反馈的迭代点：接触瞬间的镜头下压（camera kick）尚未做；上抬与前捅的幅度在玩家视点下的观感；左手推掌与回握的衔接。参考视频存 `test/uzi_ref/uzi_ref.mp4` 本机留档。
- 快捷槽无剑时提示由「需剑类」改为「需剑/枪」；技能页描述同步双武器版本。

## V2 实测结论与挂起（2026-09-17 最终）

V2 实测被用户否决：「根本不合格，跟视频参考一点都不像，枪械模型飞出去了」。定位到**武器搬运变换 bug**：武器组刚体搬运的乘法顺序写反、且对组件空间变换重复做了一次世界→组件转换，每帧给枪乘上垃圾变换直接飞出视模——该 bug 自手枪版首版即存在，导致历次实测看到的都是枪飞，动作本体从未被有效评估。bug 已修（相机空间求「目标手×入场手⁻¹」差值再一次性转回网格空间），修复后未经用户确认。

**用户决定：手枪砸击留到下次开发。** 当前状态：剑版快速进战（配重锤）功能完整可用；手枪砸击代码保留但视为挂起候选，重做入口与教训沉淀见 [手枪握把砸击尝试](../../skills/ue5-fps-arms-animation/references/pistol-grip-bash-attempt.md)。本次无确认退役文件，未走 trash 归档。

## 未测试范围

未运行游戏与任何验收；未新增测试命令或验收脚本（项目规则：检查/验收由用户发起）。F 专属槽轮：Game 目标编译链接通过（含 UE5.8 格式串编译期校验修正：`FString::Printf` 的 `%s` 实参必须解引用为 `TCHAR*`）；Editor 目标因用户编辑器开启（Live Coding 占用）未重建，当前编辑器 DLL 缺 F 槽与正式伤害文案，重启编辑器前后由 UBT 补建。待实机确认：F 槽显示与冷却读秒、无剑「需剑类」变暗、拖动高亮不落 F 槽、F 触发与第四击动作观感、伤害数值与面板分摊、击退/眩晕表现、连击排队、非剑武器按 F 的忽略路径、击杀修炼与升级提示、旧档迁移。
