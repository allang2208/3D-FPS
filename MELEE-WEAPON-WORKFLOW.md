# 武器标准工作流 · 近战

当前宿主与 Git 根目录：`D:/FPS3D/FPSGAME`。

2026-09-19 当前剑类普通连击：右向左横斩 → 左向右横斩 → 突刺 → 返回第一段横斩，按三段循环。第四段配重锤攻击已从普通连击移除；独立快速近战技能继续使用配重锤动作。改造栏只列第二段横斩与第三段突刺的连击伤害。本次未测试，由用户测试。

- [模块化拆分与可替换改造件](skills/ue5-weapon-workflow/references/modular-melee.md)：五栏目/四实体、原装安装端、无缝过渡、剑身符文、共用装配和长柄手部联动。
- [符文长剑模块化与改造栏](Docs/Weapons/rune-sword-modular-20260919.md)：苍蓝星辉的独立模块、专属图标、长柄联动与近战组合实值；未测试，由用户体验。
- [寒晶模块化成品与本次发布](Docs/Weapons/frost-sword-modular-publication-20260919.md)：用户确认结果、当前作者入口、归档与 Git 发布边界。

- [近战标准](skills/ue5-weapon-workflow/references/melee.md)：资产与物品接入、轻重攻击、三段连击、范围判定、真实突进、镜头和防御机制。
- [双手近战动作](skills/ue5-fps-arms-animation/references/two-handed-melee.md)：握点、剑身翻面、肩肘腕支撑、重定时和未接受的格挡尝试。
- [符文剑当前基线与继续入口](Docs/Weapons/runesword-baseline-20260914.md)：已接受内容、当前参数、素材依赖和暂停状态。
- [寒晶·双手剑](Docs/Weapons/frost-crystal-sword-20260915.md)：用户指定 Meshy 模型、同骨架双手动作复用、独立物品及仓库发放。
- [高地·双手剑](Docs/Weapons/highland-claymore-20260922.md)：选定 Meshy 母版、四类模块与五栏改造、共用配重适配、原生蓝色符文、仓库发放；已导入和常规构建，未测试。
- [唐刀](Docs/Weapons/tang-dao-20261002.md)：用户提供 GLB、双手握持、四类模块和五栏改造、共享配重、仓库发放；本轮后台保存与构建范围见作者目录，未测试。
- [近战背包兜底图标](SourceAssets/HighlandInventoryIcon20260923/README.md)：捕获与 `Icons/<id>.png` 兜底的两层关系、384×768 纵向 91% 构图约定、高地与寒晶缺图的原因和 `-Definitions` 定向重导；两图已重导，未做游戏内验收。
- [枪械快速近战最终整理（2026-09-19）](Docs/Weapons/quick-melee-publication-20260919.md)：M4 N、AKM／ASH-12 适配、QBZ191 O 后握把修复，以及 recover 直接衔接当前待机；用户确认成功结束。J／L／M 废案已归档，有效作者依赖保留。
- [快速近战 recover](Docs/Weapons/quick-combat-recovery-20260919.md)：归位在收势内完成，动作和业务共用时钟，消除结束后二次回正。
- [本轮整理与发布](Docs/Weapons/melee-publication-20260914.md)；[仓库规则](WORKFLOW.md#8-仓库整理与推送)。

**状态按分项记录。** V18/V19 格挡是历史未接受尝试；后续 V21 格挡已获用户接受。2026-09-19 用户确认寒晶剑模块拆分、配重锤修订、符文荧光及三款握把符合预期。本轮为流程沉淀和仓库整理，不重新运行游戏验收。
