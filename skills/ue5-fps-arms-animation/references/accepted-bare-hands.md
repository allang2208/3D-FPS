# 认可的裸手：动画开发与默认视模

**弓当前派生（2026-09-25）：** 视模与八段动画位于 `/Game/Weapons/DarkBow20260925/ContactV9/`，共享 ArmsV4 Skeleton 和装备。掌面局部修补未覆盖共同 V7 母版；已保存，尚待用户游戏确认。V2/V3 错误绑定与 V8 爪形均不能作为认可基线。绑定、完整抓握和指腹接触方法见 [弓手型与弦接触](bow-hand-string-contact.md)。

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
7. 新弓同样以认可裸手为基准，使用自己的原生绑定。当前 Bow 共享已纠正的 ArmsV4 骨架、使用 ContactV9 表面和动作；不把其他武器的逆绑定直接套到 Bow。结构与数据合同见 [第一人称弓与部件表](../../ue5-weapon-workflow/references/first-person-bow-parts.md)。

## 手动采样的动画播放合同

武器组件按手动采样播放：只 `PlayAnimation` 一次 → `SetPlayRate(0)` → 每帧 `SetPosition(秒)`（循环段取模、单向段钳住）
→ `TickAnimation(0,false)` → `RefreshBoneTransforms()`。每帧重新起播会让手臂停在片段开头。
参考片段（如 Paragon Sparrow 的 `idle` / `RMB_Drawback`）的时长只说明节奏，不能宣称已复现动作。
Bow 提取实际手／肘轨迹、保持裸臂原骨长，并制作握把和勾弦接触标记。阶段时间比例映射到实际片段全长；
动作里已包含拉距曲线时不要重复用拉距重映射。制作记录见工程 `Docs/Weapons/dark-bow-actions-v2-20260925.md`。

Bow 是在原有 20 个 profile 之外新增的原生系列。新动作和装备尚未经过运行／视觉验收；第三人称继续使用其对应身体骨架和装备网格，不直接套用第一人称原生绑定。
