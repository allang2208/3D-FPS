# 认可的裸手：动画开发与默认视模

用户于 2026-09-25 明确指定：以后新增动画以当前认可的这套裸手进行开发，默认也是这套。该选择替代旧的原版带手套默认手模。

## 基准资产

工程根为 `D:/FPS3D/FPSGAME`。以下路径相对工程根：

- 共同表面母版：`SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json`。
- 按各武器原生参考姿态制作的几何与权重：同目录 `Authored/<Profile>.json`。
- 可编辑源：同目录 `Editable/<Profile>_BareArmsV7.blend`。
- UE 裸臂：`/Game/Characters/ModularOutfit20260924/BarePalmV7/<Profile>/SK_<Profile>_BareArmsV7`。
- 运行配置：`Content/ColdSteelData/modular_outfits.json`；`native_bare_arms=true` 表示裸手已经写入基础视模。

项目详细制作记录：`Docs/Characters/bare-palm-native-default-v7-20260925.md`。后续手套、衣物制作与接入统一按 [第一人称装备标准工作流](first-person-equipment-workflow.md)；现有手套案例见工程 `Docs/Characters/fitted-gloves-animation-sharing-20260925.md`。

## 后续制作约定

1. 新增、迁移和调整枪械、剑、工具、施法、攀爬等第一人称动画时，作者场景以这套裸手、裸臂作为可见手模，保留已认可的掌形、指腹、手腕收缩、腕臂线条和皮肤材质。
2. 沿用每个武器的原生骨架、参考姿态、骨长及蒙皮。统一裸手外观不等于把 M4 的绑定矩阵直接复制给 ASH12、M16 或其他参考姿态不同的骨架。新 profile 从共同母版生成对应原生绑定派生。
3. 游戏默认、首次进入、切换到新武器及未装备手套时，基础视模直接显示裸手。新武器接入时完成裸手写入及 profile 配置，不能先展示原版手套再异步覆盖。
4. 手套、衣袖按该手型制作网格、蒙皮及覆盖边界，复用源动作。厚重装备若影响握持，再按接触类别局部修正；不为每件装备复制整套动作，也不为适配某副手套改动全局裸手母版。
5. `OriginalSources` 用于读取原生绑定或恢复历史装备，`OriginalGloves` 用于原版战术手套装备；它们不再是新增动画的可见手模默认。历史动画轨道和机械时序仍可复用。
6. 用户确认的是这套裸手基准，不代表所有未来动画或装备已获验收。维持后台制作、保存；未经明确要求不自动运行游戏、测试或截图。

当前第一人称已有 20 个 profile。第三人称继续使用其对应身体骨架和装备网格，不直接套用第一人称原生绑定。
