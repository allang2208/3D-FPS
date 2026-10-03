# 大盲注：手枪神话后缀（2026-10-02）

## 用户确定的合同

- 附魔卷轴「大盲注」：神话稀有度、后缀、只可用于 `weaponType == pistol` 的武器。
- 附魔手枪每次命中敌人获得 1 层「赌注」，每层暴击伤害倍率增加 0.5，上限 5 层。
- 整组持续 30 秒；每次命中刷新到 30 秒，满层命中也刷新。到期一次性清除所有层数。
- **暴击命中新加的一层也计入本次伤害，随后清空全部层数。**
- **仅带「大盲注」附魔的手枪暴击使用并消耗赌注。**其他武器、未附魔手枪和法术不消费。双持两把都附魔时共享角色的赌注；单独附魔一把时，另一把不增加、不使用、不消耗。
- 枪口持续呈现金色脉冲光芒，外观由实际武器附魔驱动，无赌注时也显示。

## 数据与 UI

`enchant_scroll_big_blind` / `bigBlind`，神话卷轴沿用统一写实卷轴图标、1×2 占格和 99 叠放；沿用狂暴神话卷轴的 16000 售价与 3200 魔尘费用。深度 8 起的既有掉落池中权重 1，每次 1 张。

`enhancement.json` 完整效果键为 `bigBlind`、`wagerCriticalBonusPerStack=0.5`、`wagerSeconds=30`、`wagerMaxStacks=5`。现有附魔台的后缀替换、前缀保留、物品命名、库存消费和 `_enchantData` / `_enchantEffects` 存档路径自动承载该选项。

附魔预览、武器提示与 `wager` 状态说明接入相同语义。状态栏直接读取真实赌注层数及绝对游戏时间到期点，显示整组剩余时间和当前倍率增量。

## 命中与暴击结算

`ColdSteelCombat::BigBlind` 从实际手枪物品读取完整参数。`ColdSteelSkills::Snapshot` 捕获攻击来源的参数，覆盖子弹和该手枪的快速近战；已经发出的子弹保留发射时的附魔身份。

共享 `ApplySkillWeaponHit` 在有效敌人命中时先 `AddWager`，随后把赌注增量加到同一次暴击倍率。倍率公式是 `1 + 原暴伤加成 + 层数 × 0.5`，所有物理/魔法面板分量共用一次暴击。例如原暴击 1.5 倍，5 层时为 4.0 倍；第一发即暴击则新增 1 层后为 2.0 倍。

暴击先捕获加成并清空，再调用受击伤害流程，避免伤害回调重复消费同一组层数。随机暴击与要害暴击都使用同一路径；命中计数独立于护甲是否吸收伤害。墙壁、采集目标、尸体与友方不加层；继承已结算伤害的弹射不再次增层或应用暴击。

赌注复用 `UCombatStatusFormula` 既有 Tick，使用绝对游戏时间到期；命中前读取已到期的有效层数，超时后从 1 层开始。死亡及复活清理，不写入角色存档。不增加独立伤害 Tick 或每帧 JSON 读取。

## 枪口金色脉冲资产与接入

- 原创解析材质源：`SourceAssets/BigBlind20261002/BigBlindMuzzlePulse.hlsl`。
- 后台作者入口：`Tools/Weapons/build_big_blind_glow.py`。
- 保存资产：`/Game/Weapons/BigBlind20261002/M_BigBlindMuzzlePulse`。
- 保存回执：`Saved/BigBlind/authored.json`，仅脚本落盘不等于资产已保存，以 commandlet 的实际保存结果为准。
- `UFPSWeaponFXComponent` 每把附魔手枪只保留一个 8 cm 发光卡片、一个不投影的 32 cm 小光源，周期 1.4 秒；开镜降低亮度。材质保留深度遮挡、羽化及曝光补偿，颜色为金黄。
- 材质异步加载，软引用进入 cook；不在命中/每帧同步加载。复用既有特效 Tick 和枪口接口，包含主手真实枪口、消音器出口与副手独立出口。检视、换弹和配件变更继续跟随当前出口。
- 主手档案刷新与副手设备刷新各自配置实际物品；卸下、后缀替换和退出双持隐藏效果；专用服务器不创建外观组件。

## 交付边界

按用户规则，仅后台开发、必要构建及资产保存，不启动 UE 编辑器或游戏，不运行测试、渲染或验收。玩法及视觉由用户自行测试。

2026-10-02 实际交付：后台 Python commandlet 返回成功并保存 `M_BigBlindMuzzlePulse.uasset`，`Saved/BigBlind/authored.json` 记录实际保存对象。Game 目标已执行必要构建，本次命中/状态/特效/预览源文件完成编译，但全目标被并行技能文件的错误阻塞：`FPSBlizzardComponent`、`FPSElectricMagicComponent`、`FPSFireMagicComponent`、`FPSHolyLightComponent`、`FPSIceSpikeComponent`、`FPSIceWallComponent`、`FPSLightningComponent`，主要为 `NetCast::Send` 的 `AActor*` / `APawn*` 不匹配、组件调用不存在的 `GetGameInstance` / `HasAuthority` 和暴风雪指针数组遍历。日志为 `Saved/BigBlind/gameBuild.log`；返回 `OtherCompilationError`。未修改这些并行技能文件，未生成新的 Game 可执行文件；Editor 构建未继续。源码/数据和已保存材质完成，新二进制接入仍待上述编译阻塞解除后构建。
