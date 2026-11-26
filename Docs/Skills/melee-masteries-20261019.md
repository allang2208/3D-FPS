# 刀剑精通与钝器精通（2026-10-19）

## 技能定义

“剑精通”显示名改为“刀剑精通”，保留 `swordMastery` 存档键及已获得等级、经验，仅双手刀剑武器享受伤害与普攻速度加成。新增 `bluntMastery`“钝器精通”，适用 `category=weapon_melee` 且 `weaponType=blunt` 的全部钝器武器，当前包括双手战锤。采集用斧、镐、铲和空手、枪托、法杖不因造成钝击伤害自动归类为钝器武器；剑柄动作仍属于所持刀剑的精通。

两个技能均为被动、初始 1 级、上限 20 级，无蓝耗、无主动冷却，不增加快捷栏主动施法入口。刀剑精通每级固定武器伤害 +1，20 级 +20。钝器精通按用户后续要求改为每级武器伤害 +1.25%，20 级 +25%，替换原固定伤害，不额外叠加 +20。

两者普通攻击间隔仍每级减少 1%；实值速度为 `1 / (1 - 0.01 × 等级)`，20 级等效普攻速度 +25%。等级、经验、修炼方式和图标保留。钝器新成长见 [百分比伤害成长](blunt-mastery-damage-growth-20261019.md)。

伤害通过 `AdditionalWeaponDamage`、`ProcessedDamage` 进入已有武器伤害公式，武技按原公式继承武器伤害。修复旧版刀剑固定伤害误加给其他武器的问题。攻速通过 `MeleeMasteryIntervalMultiplier` 分流，普通刀剑／锤类的动画、接触与后摇同源。双手锤重击释放剔除本精通新增的普攻倍率，上挑、大旋风、快速近战、蓄力与冷却继续走独立规则；雷电迅捷的明确动作加速仍生效。

## 修炼与保存

- 对应武器有效命中 +1 XP，直接击杀 +10 XP；同一次攻击有效命中至少两名敌人，额外 +3 XP，仅一次。各项可以叠加，暴击无额外精通经验，原暴击技能修炼继续生效。
- 升下一级所需经验为 `300 × 当前等级`。满级停止积累；两种精通独立成长。
- 不计挥空、尸体、友方、召唤物、`NoSkillTraining` 目标及采集资源。伤害确认后修炼；同次攻击目标去重，多目标额外奖励由已确认命中数决定。
- 刀剑普攻、重击、上挑、冲刺、大旋风沿现有技能快照传递精通；锤类普攻扇区、重击／冲刺冲击波、上挑、大旋风和快速近战分别接入。
- 网络命中附带动作序号，服务端依据装备重新确定精通及伤害，并从有效命中重新计算多目标额外经验。波形和锤类主体命中在服务端直接结算，沿原去重集合处理。
- Profile v25 只补钝器进度，v24 已有雷电迅捷和刀剑进度保持；旧档更早版本继续原迁移。技能目录、开发工具、升级提示、技能列表、详情与修炼条一并接入。

## 图标与界面

使用 `ue5-skill-magic-workflow`、`ue5-ui-umg-slate` 与内置 imagegen 工作流。银色圆角正方框、石墨底、左上柔光，框外透明，主体完整留框内，无文字。刀剑采用 V2 并列构图的双手直刃长剑与唐刀，刀身、护手和握柄保持同轴；初版交叉图被用户指出扭曲后重做，旧图归档到 `trash/melee-masteries-20261019`，原路径、大小及 SHA-256 见 `retired-icon.json`。钝器使用双手战锤。PNG 为实际 UI 图源，Texture2D 另按 UI 分组、EditorIcon 压缩、sRGB、NeverStream 和最大 512px 保存。

图标源、提示词和记录位于 `SourceAssets/MeleeMasteries20261019`；正式路径为 `Content/ColdSteelData/Skills/blade_mastery_cold_steel.png` 和 `blunt_mastery_cold_steel.png`。`Tools/UI/prepare_cold_steel_skill_icons.py` 已接新恢复清单。导入入口为 `Tools/Skills/import_melee_mastery_icons.py`，实际保存结果记入 `asset-receipt.json`。

UI 沿用既有被动技能卡片和详情页，只增加钝器卡片及对应描述。图标初始化加载一次并持有引用；列表、详情、升级提示共用技能定义，不新建面板、焦点路径或 Tick 加载。效果对比显示本级／下一级，普攻速度保留一位小数。

## 制作与交付边界

源码变更前副本、分段接入记录、构建日志和资产保存记录位于 `SourceAssets/MeleeMasteries20261019`。两枚最终图标已通过后台 author host 导入并保存 Texture2D，日志 `import-author-01.log` 退出码 0，实际资产路径见 `asset-receipt.json`。后台作者报告的两条警告来自已有 Paragon 演示地图的 Lighting_Background 数据。

本次不主动进行游戏、联机、UI、性能或视觉验收；编译和资产保存完成后由用户试玩。最终构建结果以同目录回执为准。

- `FPSGAME Win64 Development` 构建成功，退出码 0；UBT 报目标已是最新，用时 6.11 秒。日志：`FPSGAME-build-1.log`，回执：`FPSGAME-build-receipt.json`。
- `FPSGAMEEditor Win64 Development` 中间共享构建成功（62.58 秒），日志归档为 `FPSGAMEEditor-success-shared.log`。随后本任务增量构建遇到共享双持手枪新增代码的编译错误：生产工具指针隐式转 bool、直接访问模型上不存在的 `ActiveWeaponSlot`。仅改为显式非空比较及从既有 `Snapshot()` 取槽位，没有改动手枪玩法；修复前副本保留在任务 source-before 下。最终构建回执以该修复后的记录为准。
- 修复后本任务 `FPSGAMEEditor-build-2.log` 常规构建成功（26.94 秒），已链接基础 DLL，退出码 0。后续 Game 增量构建遇到共享 `FPSPlayerBodyTypes.h` 在编译期间更新、反射生成代码失配；安排 UBT 正式 `-ForceHeaderGeneration` 构建，无清理、还原或手改生成头文件。
- 共享 Game 重建随后成功（210.31 秒，297 个构建步骤，已链接 `FPSGAME.exe`），日志归档为 `FPSGAME-success-final-shared.log`。本任务最后的 `FPSGAME-build-3.log` 也成功（7.66 秒，目标已是最新），退出码 0，最终回执为 `FPSGAME-build-receipt.json`。Editor 和 Game 必要构建均已完成，未启动游戏验收。
