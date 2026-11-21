---
name: ue5-clothing-workflow
description: 制作和修复 FPSGAME 玩家服装的上衣裤装衔接、扎腰、内外层、腰臀覆盖与裤靴配对，维护现有及新增服装的组合工作流。武器手部动画和怪物衣物分别走手臂、怪物技能。
---

# 玩家服装与搭配

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

遵守用户规则：默认后台制作、必要构建和保存；不主动运行游戏、截图、测试或跨对话协调。用户明确要求排查时，仅执行相关范围的检查。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

工程为 `D:/FPS3D/FPSGAME`。先读当前 `AGENTS.md` 与 [服装腰部工作流](../../../Docs/Characters/garment-waist-workflow.md)，以实际 `Content/ColdSteelData/modular_outfits.json` 和 `FPSModularOutfitComponent` 消费分支为准。资产操作沿 [后台接入规则](../ue5-auto-assistant/references/editor-open-development.md)。

## 衔接制作

- 区分扎腰短衣、原生躯干材质加饰边、外穿长衣与法袍内层。保留款式身份；不要将所有上衣统一缩短或所有裤子改紧身。 原因：不同衣型具有不同遮盖和搭配目的，统一裁短或收紧会改变已经认可的款式。
- 每次按槽枚举上衣、裤子、普通／靴型实际网格、世界／本人身体和身体骨架。已有配对只证明对应修订；不能从一套皮衣推广成全部衣服已完成。
- 当前 Jason 扎腰入口为 `Tools/GarmentWaist/run.ps1`；款式、外层槽登记在 `Tools/GarmentWaist/policies.json`。新增上衣先补穿法与原生源，新增裤子先保存普通／靴型。其他骨架须有对应作者源和生产配方。
- 从真实裤腰取得截面和绑定，内侧留搭接，衔接带向上渐变回衣身。外层、内衬、包边与装饰使用同一变形，保留必要皮肤和腿部覆盖。不能用全局缩放、零骨骼或隐藏整段身体解决开缝。 原因：装备组合依赖具体身体与服装轮廓，通用裁切或单件修复不能覆盖所有配对。
- 保留已认可野行上衣／皮裤配对、ST6 原生躯干与袖子、法袍完整腿部及裙摆实时包络。参考数值仅适用于对应模型。 原因：用户认可的是具体母版和观感，换成另一版本会改变已有接触或外观基线。
- 保存完整资产与 LOD 后才按字段发布配对。保留无裤子时原形；同时提供世界和 Owner 版本，沿已有异步切换。保持实际裤网格优先、物品映射次之、默认扎腰回退最后；新模型仍需专用适配。 原因：配对数据会立即驱动服装切换，完整资产和正确优先级才能保留无裤子原形及世界、Owner 一致性。
- 源资产、裤腰、算法或绑定变化时重制受影响配对；使用散列确认续接输入，不把旧 `published.json` 当当前验收。交付明确资产保存、本地接入及未进行的动作／游戏验收。
- 上衣与裤腰保存发布后运行 `Tools/BackpackFit/run.ps1`，补做七款背包在双身体上的受影响配对。工装/裤腰入口已调用；其他新服装入口遵循同一顺序。规则和回执边界见 [背包贴合制作](../../../Docs/Characters/backpack-contact-workflow.md)。

用户要求排查远景衣物闪面或材质错位时，从实际穿搭表列出身体、姿态和对应网格，再读每个 LOD 的材质槽映射和区段。简化后的区段数可以变少。若 UE 仅在加载某一派生包时报告自动修复区段索引，单独重存该包并重新加载，核对材质槽和各 LOD 区段；近景母版可能始终正常。

## 按需资料

- [衣物表面、厚度与材质](../ue5-fps-arms-animation/references/glove-clothing-surface-production.md)
- [共用身体与裤鞋覆盖](../ue5-fps-arms-animation/references/shared-owner-body-and-lower-equipment.md)
- [长袍连续覆盖与布料时序](../ue5-fps-arms-animation/references/garment-continuity-and-cloth-timing.md)
- [原生手臂和装备外观](../ue5-fps-arms-animation/SKILL.md)

当前生产流程没有将未来任意低腰、异形裤或新身体自动视为无穿模。用户要求检查时列出实际覆盖矩阵，区分静态几何、动作形变、运行时和多人结果，不以配置字段存在代替视觉结论。

- 腰带作为独立槽位接入、男女腰臀包络和侧挂箭袋，读取 [腰带与箭袋](../ue5-item-asset-workflow/references/belts-and-quivers.md)。

- 女体独立领口的头身表面、内折边及 LOD 配对见[ST6 女性领口](references/st6-female-collar.md)。
