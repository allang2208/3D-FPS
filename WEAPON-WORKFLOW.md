# UE5 武器与手臂标准

当前工程入口为根目录 `FPSGAME.uproject`，完整本机宿主及 Git 工作目录都是 `D:/FPS3D/FPSGAME`，直接在该目录提交和推送。

- [近战武器标准](MELEE-WEAPON-WORKFLOW.md)：双手握持、轻重攻击、三段连击、真实突刺跨步、命中判定与防御；符文剑格挡动作尚未满意，暂停继续。
- [枪械标准](skills/ue5-weapon-workflow/SKILL.md)：模型/许可、骨架/挂点、ADS、枪匠、装备与存档。
- [手臂动画](skills/ue5-fps-arms-animation/SKILL.md)：自然抓握、甩匣、取弹插入、拉栓、MAT 和音效。
- [当前 M4 合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)：参数应用前核对实际 C++ 加载。
- [发布规则](WORKFLOW.md#8-仓库整理与推送) 与 [资产恢复](Docs/AssetSetup.md)。

M4 普通/空仓都甩掉旧弹匣、镜头外取新匣、左手包握插入；空仓保留拍击，装备按其拉栓动作处理。手枪按实际源动作和机械状态适配，M1911 采用拔枪与空仓套筒释放，支持装备途中开火和 ADS。不同枪型重新校准接触和时序，个人技能源与工程镜像保持同步。

- [枪身与配件材质统一](skills/ue5-weapon-workflow/references/weapon-finish.md)：每枪以自身当前主体涂层为基准，统一所有改造件的金属区域，保留非金属、刻字与光学消光层；跨枪复用分别制作材料变体。
- [本轮整理与发布](Docs/Weapons/weapon-publication-20260913.md)

- [手枪标准](skills/ue5-weapon-workflow/references/pistols.md)：末发/空仓、快速拔枪输入、精确装配、换弹时钟、展示和材料生命周期；[M1911 开发审计](Docs/Weapons/m1911-development-audit-20260913.md) 记录本次修复及检查范围。
