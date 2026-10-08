# 异形怪物减面、重拓扑与当前引用排查（2026-10-06）

结论：没有全部完成。当前 7 类 M 系列中，悬钟 M-09、螺柱 M-14、沉匣 M-10、伏窥者 M-08 共 4 类仍使用超过 100 万三角面的活体网格，并且仅有 LOD0。它们的软体尸体也保留同等面数。减面、局部拓扑修整、完整重拓扑是不同完成状态，不能把已经绑骨、导入或能够播放动作视为都已完成。

## 范围与读取口径

- 读取时间：2026-10-06T22:24:16.141043 至 2026-10-06T22:24:25.484087，本机时间 UTC+8。
- 以 DevelopmentSpawnComponent 当前登记的 12 个异形入口为范围，共 11 类独立活体网格（小皮肤手与巨手共用），包括全部 7 类 M 系列、手脑、毒蛆、巨手及百目炉渣。常规人形僵尸与犬狼未纳入本表。
- 加载实际蓝图/原生类默认对象，追踪 VisualMesh 或主网格组件；检查关联的 8 个独立软体尸体网格。没有把 SourceAssets 中的原始高模、旧版本或候选模型当作当前显示模型。
- 面数统一指 UE 渲染三角面，LOD0 取当前网格对象的渲染统计标签，低级 LOD 用 GeometryScript 读取实际 RenderData；表内是实际面数，不是减面比例目标。
- 本表所有活体、尸体网格的 NaniteEnabled 均为 False。LOD 数量包含 LOD0；“1 级”即没有更低精度的距离 LOD。
- 接入指当前类默认引用和已保存的资产依赖；没有运行游戏，也没有检查关卡实例可能单独设置的覆盖项或测量画面实际选中的 LOD、帧率。
- 本轮只写排查脚本、原始统计和报告，没有减面、重导入或保存游戏资产。命令行读取前后 dirty content package 列表相同；M07 包在采集开始前已脏，本次未保存。

## 活体结果

| 怪物 | 当前各级三角面（LOD0 起） | LOD0 材质分段 | 排查优先级 | 减面/重拓扑状态 |
|---|---:|---:|---|---|
| 悬钟 M-09（天花板） | 2,179,898 | 6 | 高 | 整身减面未完成；V16 局部重建腕部、肩部连接，不能算整身重拓扑 |
| 螺柱 M-14 | 1,936,942 | 4 | 高 | 仍沿用原高密度表面；V15 支撑蒙皮及 V21/V22 动作不等于减面 |
| 沉匣 M-10 | 1,258,623 | 4 | 高 | V5 局部重建内口、调整表面及绑骨；整身减面未完成 |
| 伏窥者 M-08 | 1,250,160 | 2 | 高 | CanineV03 仍是高密度网格；未见整身减面/重拓扑接入证据 |
| 涡电匣 M-25 | 349,998 / 119,998 / 39,996 / 9,984 | 1 | 中 | 已从 6,524,740 面减至 349,998 面并接入四级 LOD；保 UV 减面，不等于完整重拓扑 |
| 手脑 | 230,023 | 6 | 中 | 局部表面修整与细分；源回执明确 complete_anatomical_retopology=false |
| 盲祷者 M-07 | 207,321 / 82,927 / 80,487 | 2 | 中 | 已有身体/膜片显示网格优化；末级 LOD 降面幅度不足，非完整整身重拓扑 |
| 螳螂-M27 | 197,761 / 98,879 / 39,551 / 15,818 | 1 | 中 | LOD0 沿用 Meshy 原网格，BindingV2 未减面；已生成并接入三级低精度 LOD |
| 百目炉渣 | 100,000 / 44,999 / 13,999 | 1 | 较低 | 原 2,896,776 面已减至 100,000 面，配合法线烘焙和三级 LOD；不等同完整重拓扑 |
| 毒蛆 | 40,336 | 1 | 较低 | 有 QuadriFlow 重网格、贴合、UV 与高低模 PBR 烘焙；StyleV1 保留这套拓扑 |
| 异变巨手 | 27,270 / 13,634 / 5,454 | 1 | 较低 | Meshy 四边形重网格已接入，本地保留四边面绑骨；另制低精度 LOD |
| 小皮肤手 | 27,270 / 13,634 / 5,454 | 1 | 需关注尸体 | 共用巨手网格；BeginPlay 固定 LOD2，活体实际 5,454 面 |

优先级针对几何制作缺口，不代表已测得性能瓶颈。项目对普通全身怪物的 3–10 万面区间只是制作参考，复杂近景个体允许更高；不能仅凭超出区间就要求损伤轮廓或变形质量。四只百万面且无距离 LOD 的对象是本轮最明确的高面数异常。

## 需要特别处理的差异

1. **悬钟现状不能沿用早期 189 万面的记录。** 当前 /V04/SK_M09 实际导入来源为 ArmContinuityV16，统计为 2,179,898 面。局部腕肩连接重建已经接入，但没有整身减面和距离 LOD。
2. **沉匣是 M-10；涡电匣是 M-25。** 沉匣当前 SurfaceRigV5 为 1,258,623 面、单级 LOD；涡电匣 OptimizedV01 已真正切到 349,998 / 119,998 / 39,996 / 9,984 面，不能混为“沉匣都优化了”。
3. **手脑不是完整重拓扑已完成的样板。** 当前 230,023 面、6 个渲染分段、没有距离 LOD；surface_v07 回执明确只有 local_refinement，完整解剖重拓扑为 false。
4. **盲祷者末级 LOD 仍很密。** 82,927 → 80,487 面仅再减少约 2.9%，不能将 15% 的制作目标当作实际完成。当前蓝图 bUseCoherentGillMotion=false，布料恢复/暂停距离为 12 m / 16 m；原生代码在布料启用和渐退期间锁定 LOD0，远处才释放。此处读取的是配置和控制逻辑，没有实测距离切换。
5. **螳螂已有低精度 LOD，但 LOD0 没有减面。** BindingV2 制作回执明确保留 Meshy 原网格，197,761 面；不能把 LOD 生成或重新绑骨写成整身重拓扑。

## 软体尸体结果

以下各尸体资产均只有 LOD0。M14SoftBodyDeath.cpp 的 Display->SetForcedLOD(1) 将显示固定在 LOD0；活体隐藏后由尸体替代显示，因此不应把活体与尸体面数相加描述单只可见怪物。

| 对应怪物 | 尸体三角面 | LOD 数 | 结论 |
|---|---:|---:|---|
| 悬钟 M-09（天花板） | 2,179,898 | 1 | 保留百万面表面，死亡后没有距离降面 |
| 螺柱 M-14 | 1,936,942 | 1 | 保留百万面表面，死亡后没有距离降面 |
| 沉匣 M-10 | 1,258,623 | 1 | 保留百万面表面，死亡后没有距离降面 |
| 伏窥者 M-08 | 1,250,160 | 1 | 保留百万面表面，死亡后没有距离降面 |
| 涡电匣 M-25 | 349,998 | 1 | 活体远级约 1 万面，尸体始终约 35 万面 |
| 手脑 | 186,560 | 1 | 尸体删除了攻击分支，面数低于活体，但仍无距离 LOD |
| 毒蛆 | 40,336 | 1 | 未配套尸体距离 LOD |
| 异变巨手 | 27,270 | 1 | 巨手/小皮肤手共用；小手活体 5,454 面，尸体回到 27,270 面（5 倍） |

普通软体尸体的 Binding.Data 是未开放给 Python 读取的原生属性。本轮确认活体有 MonsterSoftCorpseBinding，再读取网格包唯一的尸体 DataAsset 硬依赖及该资产实际 CorpseMesh；这条链与制作 sources.json 一致。螺柱则直接读取当前角色的 SoftBodyDeathData.CorpseMesh。没有因 Python 属性不可读就把绑定判成缺失。

安装工具明确移除了未重绑的旧尸体低精度 LOD，所以后续补尸体 LOD 必须同时完成对应级别的软体绑定；仅删除 SetForcedLOD 或直接复制活体 LOD 会破坏死亡变形。

## 建议的后续制作顺序（本轮未执行）

1. 优先处理螺柱、悬钟、沉匣、伏窥者四只的游戏显示网格：保留高模源和已认可轮廓，区分嘴、触须、关节、硬件与大块躯干的密度，完成必要局部拓扑、权重转移和细节烘焙，再制作距离 LOD。不能整只统一比例粗减。
2. 同批制作对应软体尸体的显示网格及分级绑定，避免只更换活体。涡电匣和小皮肤手的尸体分级也需补齐。
3. 再处理手脑的距离 LOD 与局部拓扑、盲祷者末级 LOD 的保留约束；螳螂按实际近景用途决定是否进一步减 LOD0。毒蛆可按群体密度补远级 LOD，但它当前 40,336 面不属于百万面异常。
4. 每只制作完成后，接入必须覆盖当前蓝图/原生默认引用、动画蒙皮、软体尸体与制作回执；体验和性能测试按用户后续明确范围进行。本报告不承诺减面后的帧率收益。

## 当前实际资产路径

### 悬钟 M-09（天花板）

- 入口：`/Script/FPSGAME.HangingBellM09`
- 活体：`/Game/Monsters/HangingBellM09/V04/SK_M09.SK_M09`
- 尸体：`/Game/Monsters/SoftCorpseV1/HangingBellM09/SK_HangingBellM09_SoftCorpse.SK_HangingBellM09_SoftCorpse`

### 螺柱 M-14

- 入口：`/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14.BP_SpiralPillarM14_C`
- 活体：`/Game/Monsters/SpiralPillarM14/SK_M14_SupportSkin_v15.SK_M14_SupportSkin_v15`
- 尸体：`/Game/Monsters/SpiralPillarM14/SK_M14_XPBDCorpse_v19.SK_M14_XPBDCorpse_v19`

### 沉匣 M-10

- 入口：`/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler.BP_M10Mawcrawler_C`
- 活体：`/Game/Monsters/M10Mawcrawler/SurfaceRigV5/SK_M10_SurfaceRig_V5.SK_M10_SurfaceRig_V5`
- 尸体：`/Game/Monsters/SoftCorpseV1/M10Mawcrawler/SK_M10Mawcrawler_SoftCorpse.SK_M10Mawcrawler_SoftCorpse`

### 伏窥者 M-08

- 入口：`/Game/Monsters/LurkerM08/BP_LurkerM08.BP_LurkerM08_C`
- 活体：`/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03.SK_LurkerM08_CanineV03`
- 尸体：`/Game/Monsters/SoftCorpseV1/LurkerM08/SK_LurkerM08_SoftCorpse.SK_LurkerM08_SoftCorpse`

### 涡电匣 M-25

- 入口：`/Game/Monsters/VortexCofferM25/BP_VortexCofferM25.BP_VortexCofferM25_C`
- 活体：`/Game/Monsters/VortexCofferM25/OptimizedV01/SK_M25_VortexCoffer_Game_V01.SK_M25_VortexCoffer_Game_V01`
- 尸体：`/Game/Monsters/SoftCorpseV1/VortexCofferM25/SK_VortexCofferM25_SoftCorpse.SK_VortexCofferM25_SoftCorpse`

### 手脑

- 入口：`/Game/Monsters/HandBrain/BP_HandBrain.BP_HandBrain_C`
- 活体：`/Game/Monsters/HandBrain/StyleV1/SK_HandBrain_StyleV1.SK_HandBrain_StyleV1`
- 尸体：`/Game/Monsters/SoftCorpseV1/HandBrain/SK_HandBrain_SoftCorpse.SK_HandBrain_SoftCorpse`

### 盲祷者 M-07

- 入口：`/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.BP_BlindSupplicantM07_C`
- 活体：`/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18.SK_M07_BodyMotionV18`

### 螳螂-M27

- 入口：`/Game/Monsters/MantisM27/BP_MantisM27.BP_MantisM27_C`
- 活体：`/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2.SK_MantisM27_BindingV2`

### 百目炉渣

- 入口：`/Script/FPSGAME.HundredEyedSlagMonster`
- 活体：`/Game/Monsters/HundredEyedSlag/ArticulationV12/SK_HundredEyedSlag_V12.SK_HundredEyedSlag_V12`

### 毒蛆

- 入口：`/Game/Monsters/PoisonMaggot/BP_PoisonMaggot.BP_PoisonMaggot_C`
- 活体：`/Game/Monsters/PoisonMaggot/StyleV1/SK_PoisonMaggot_StyleV1.SK_PoisonMaggot_StyleV1`
- 尸体：`/Game/Monsters/SoftCorpseV1/PoisonMaggot/SK_PoisonMaggot_SoftCorpse.SK_PoisonMaggot_SoftCorpse`

### 异变巨手

- 入口：`/Game/Monsters/FleshHand/BP_FleshHand.BP_FleshHand_C`
- 活体：`/Game/Monsters/FleshHand/SK_FleshHand_Green.SK_FleshHand_Green`
- 尸体：`/Game/Monsters/SoftCorpseV1/FleshHand/SK_FleshHand_SoftCorpse.SK_FleshHand_SoftCorpse`

### 小皮肤手

- 入口：`/Game/Monsters/FleshHand/BP_FleshHandMinion.BP_FleshHandMinion_C`
- 活体：`/Game/Monsters/FleshHand/SK_FleshHand_Green.SK_FleshHand_Green`
- 尸体：`/Game/Monsters/SoftCorpseV1/FleshHand/SK_FleshHand_SoftCorpse.SK_FleshHand_SoftCorpse`

## 证据与复用入口

- 本轮原始读取：[alien-monster-geometry-audit-20261006.json](alien-monster-geometry-audit-20261006.json)。包含实际引用、逐级面数/顶点、材料、骨架、导入来源和尸体依赖。
- 汇总表：[alien-monster-geometry-audit-20261006.csv](alien-monster-geometry-audit-20261006.csv)。
- 只读采集脚本：Tools/MonsterAI/audit_runtime_geometry.py；后台入口：Tools/MonsterAI/Invoke-GeometryAudit.ps1。
- 成功读取日志：Saved/MonsterGeometryAudit20261006/read-commandlet-20261006-222400.log。此前尝试中的 JSON 数组序列化错误及受保护属性读取问题已在采集脚本中处理，最终 errors=[]。
- 当前入口：Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp。
- LOD 强制逻辑：Source/FPSGAME/Monsters/FleshHandMonster.cpp、BlindSupplicantMonster.cpp、M14SoftBodyDeath.cpp。
- 尸体接入与制作：Source/FPSGAME/Monsters/MonsterCorpseRagdollComponent.cpp；Tools/MonsterSoftCorpse/install_corpses.py；SourceAssets/MonsterSoftCorpse20261005/sources.json。
- 悬钟局部拓扑：Docs/Monsters/HangingBellM09ClawContinuityV16_20261004.md；SourceAssets/HangingBellM09Meshy20261003/ArmContinuityV16/Records/reconstruction.json。
- 沉匣局部制作：Docs/Monsters/M10Mawcrawler.md 的 SurfaceRigV5 段。
- 涡电匣减面接入：SourceAssets/M25VortexCoffer20261004/OptimizationV01/asset_receipt.json。
- 螳螂原网格：SourceAssets/MantisM27/BindingV2/Delivery/motion_manifest.json。
- 盲祷者已有减面：Docs/Monsters/BlindSupplicantM07OriginalV13.md；当前导入源为 ShoulderClothV38。
- 百目炉渣减面：SourceAssets/HundredEyedSlagMeshy20260930/RuntimeV3/geometry_receipt.json；当前正式引用为 ArticulationV12。
- 毒蛆重网格：SourceAssets/PoisonMaggot20260911/delivery/topology.json；Tools/PoisonMaggot/build_topology.py。
- 巨手四边形重网格请求及交付：SourceAssets/FleshHand20260926/Meshy/candidate01/request.json；LocalRig/input_geometry.json；author_local_rig.py；Docs/Monsters/FleshHandIntegration20260927.md。
- 手脑拓扑边界：SourceAssets/HandBrain20260910/surface_v07/surface_report.json；Tools/HandBrain/build_surface_v07.py。
- 手脑、毒蛆 StyleV1 沿用原拓扑：Docs/Monsters/MonsterStyleV1.md。
- 面数预算口径：skills/asset-model-workflow/references/geometry-budgets-by-use.md。

完成的是用户要求的资产与引用排查；未运行游戏、渲染预览或性能测试，未修改怪物游戏资产。
