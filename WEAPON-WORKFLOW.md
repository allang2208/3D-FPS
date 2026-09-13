# UE5 枪械与手臂标准

当前工程入口为根目录 `FPSGAME.uproject`，完整本机宿主及 Git 工作目录都是 `D:/FPS3D/FPSGAME`，直接在该目录提交和推送。

- [枪械标准](skills/ue5-weapon-workflow/SKILL.md)：模型/许可、骨架/挂点、ADS、枪匠、装备与存档。
- [手臂动画](skills/ue5-fps-arms-animation/SKILL.md)：自然抓握、甩匣、取弹插入、拉栓、MAT 和音效。
- [当前 M4 合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)：参数应用前核对实际 C++ 加载。
- [发布规则](WORKFLOW.md#8-仓库整理与推送) 与 [资产恢复](Docs/AssetSetup.md)。

普通/空仓都甩掉旧弹匣、镜头外取新匣、左手包握插入。普通装好直接待机，空仓保留加速拍击及枪身轻震；装备在对应腰射位置播放拉栓。其他枪型重新校准接触和时序，不照搬 M4 数值。个人技能源与工程镜像保持同步。

- [枪身与配件材质统一](skills/ue5-weapon-workflow/references/weapon-finish.md)：每枪以自身当前主体涂层为基准，统一所有改造件的金属区域，保留非金属、刻字与光学消光层；跨枪复用分别制作材料变体。
- [本轮整理与发布](Docs/Weapons/weapon-publication-20260913.md)
