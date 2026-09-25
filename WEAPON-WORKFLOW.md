# UE5 武器与手臂标准

**默认手模（用户于 2026-09-25 更新）**：新增动画和新武器统一以已认可的 V7 裸手、裸臂开发，基础视模默认也是这套。手套、衣袖适配裸手并复用动作。作者源与接入规则见 [认可的裸手基准](skills/ue5-fps-arms-animation/references/accepted-bare-hands.md)。

当前工程入口为根目录 `FPSGAME.uproject`，完整本机宿主及 Git 工作目录都是 `D:/FPS3D/FPSGAME`，直接在该目录提交和推送。

- [M4 枪托砸击（快速进战·步枪版）](Docs/Weapons/m4-stock-melee-20260918.md)：作者源 clip 路线（六握把配置各一条）、Blender 对位胶片、命中探针取枪身前段；未实机测试。
- [近战武器标准](MELEE-WEAPON-WORKFLOW.md)：双手握持、轻重攻击、连击、真实突刺跨步、命中判定与防御；包含已接受的 [模块化拆分与改造接口](skills/ue5-weapon-workflow/references/modular-melee.md)。
- [枪械标准](skills/ue5-weapon-workflow/SKILL.md)：模型/许可、骨架/挂点、ADS、枪匠、装备与存档。
- [手臂动画](skills/ue5-fps-arms-animation/SKILL.md)：自然抓握、甩匣、取弹插入、拉栓、MAT 和音效。
- [当前 M4 合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)：参数应用前核对实际 C++ 加载。
- [M16A2 发布与恢复](Docs/Weapons/m16-publication-20260920.md)：三连发、M4 换弹/近战复用、空仓拉机柄、通用配件及四款枪托封口；已获用户确认，保留最终作者依赖链。
- [M4 / M16 换弹左手抓握精度修复](Docs/Weapons/m4-m16-reload-grip-precision-20260925.md)：把抓握存成弹匣自身壳坐标系的关系再跨枪搬运，替换 M16 移植里手估的武器空间常量偏移；12 条换弹重导。方法沉淀见 [弹匣抓握跨枪配准](skills/ue5-fps-arms-animation/references/magazine-grip-registration.md)。
- [AKM / A762 换弹拇指扭曲修复](Docs/Weapons/akm-a762-reload-thumb-twist-20260925.md)：抓握把拇指根部绕自身轴扭了 67°，按 SVD 经验只重做拇指三条轨道（根部纯 swing）；30 条换弹重导。判据与改法沉淀见 [异形弹匣自然抓握](skills/ue5-fps-arms-animation/references/irregular-magazine-grip.md)。
- [发布规则](WORKFLOW.md#8-仓库整理与推送) 与 [资产恢复](Docs/AssetSetup.md)。

M4 普通/空仓都甩掉旧弹匣、镜头外取新匣、左手包握插入；空仓保留拍击，装备按其拉栓动作处理。手枪按实际源动作和机械状态适配，M1911 采用拔枪与空仓套筒释放，支持装备途中开火和 ADS。不同枪型重新校准接触和时序，个人技能源与工程镜像保持同步。

- [枪身与配件材质统一](skills/ue5-weapon-workflow/references/weapon-finish.md)：每枪以自身当前主体涂层为基准，统一所有改造件的金属区域，保留非金属、刻字与光学消光层；跨枪复用分别制作材料变体。
- [本轮整理与发布](Docs/Weapons/weapon-publication-20260913.md)

- [手枪标准](skills/ue5-weapon-workflow/references/pistols.md)：末发/空仓、快速拔枪输入、精确装配、换弹时钟、展示和材料生命周期；[M1911 开发审计](Docs/Weapons/m1911-development-audit-20260913.md) 记录本次修复及检查范围。
