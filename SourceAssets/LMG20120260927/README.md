# 201 当前制作与恢复入口

2026-09-29：原 201 已列为废案。旧生成入口、旧根 README 及废案输出移到 `trash/lmg201-rejected-20260929/SourceAssets/LMG20120260927/`。详见 [废案记录](../../Docs/Rejected/lmg201-original-model-20260929.md)。

## 当前新模型

- 模型链：MeshyRetry28 → Refine29 → Install30 → Surface32 → Detail35 的局部输入 → Repair36 → ReferenceRepair38 → HardSurface39 → Assembly40 → SightFinish41 → SurfaceReform42 → GripFinish43 → GripJunction44 → **[ClothTop45](ClothTop45/README.md)**（布料弹箱上部修复）。
- 当前完整装配以已保存 UE 主体为准，后续局部制作应重新导出现用资产。最新局部表面制作源为 `SurfaceFinish50/LMG201_SurfaceFinish50.blend`，制作输入 `SurfaceFinish50/Inputs/Body.fbx` 已含 BeltMotion49。旧 `Drum46/Inputs/Current201.fbx` 不含后续分段，不能整枪覆盖。布箱局部编辑源仍为 `ClothTop45/LMG201_ClothTop45.blend`；三个改装后握把已由 **[RearGripRestore58](RearGripRestore58/README.md)** 从原始母版恢复，S42 脚架、S41 后照门和 R38 盖壳轮廓保留。
- UE 主体：`/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。旧包名并不代表首轮旧模型。
- 原装弹匣：Magazine24；布料弹箱：[ClothReload44](ClothReload44/README.md) 换弹动画（2026-09-30 起替代 ClothFeed33 的十条换弹，旧片段已按先前清理记录归档，不直接执行旧回退入口）／ClothFeed33 分件／ClothTop45 外观；通用配件：Accessories22；ADS 衣物：ADS34；开火声：FireAudio01。
- 大弹鼓：[Drum46](Drum46/README.md) 提供 `large_drum` 改造与十条独立换弹；当前接头、源模型和图标为 **[DrumJoint47](DrumJoint47/README.md)**（2026-09-30，移除复制的原厂弹匣上段，按实际 idle 重建封闭接口）。现用网格仍在 Drum46 路径；原厂弹匣及布弹箱继续保留。
- 背包图标：沿用 [InventoryIcon48](InventoryIcon48/README.md) 规则，最新目录 PNG 已由 SurfaceFinish50 按现用装配重生成；保留实际材质色、5×2 透明画幅和 91% 居中取景。大弹鼓等改造状态继续使用既有按实例配方生成的动态图标，未实机测试。
- 布箱弹链：当前为 **[BeltFit53](BeltFit53/README.md)** 的规则子弹、独立链片与连续袋内/机匣内段；换弹为 ClothReload44.4b，后续叠加 ArmHinge55 的左臂七骨修正。旧完整 Tracks 未包含后续所有补丁，不能直接整段覆盖。
- 提把与下侧残块：H54/M55 提把被用户否决，**[HandleRemoval56](HandleRemoval56/README.md)** 已删除提把及悬挂块残片；旧方案已归档到本机 trash。闲置叶骨保留索引；当前无提把动态。
- 弹链次级运动：保留 **[Motion55](Motion55/README.md)** 的 PKM 进弹链参数（速度衰减 13/s、回拉 1050/s²、4 mm 通道）与短促开火扰动。**[FeedMouth57](FeedMouth57/README.md)** 已局部修整固定入口，给 B53 弹链让位；袋口、链位和动作保持。
- 当前完整材质绑定：`Material21/bindings.json`；最新枪体／配件表面绑定为 `SurfaceFinish50/bindings.json`。F50 由 G43/J44 私有表面家族派生，统一烤漆、钢件与聚合物；布箱继续采用 C45 的织物与独立硬接口材质，光学材质、弹链材质及内壁保留。

## 本轮细节修整

2026-09-30，[SurfaceFinish50](SurfaceFinish50/README.md) 根据整枪收尾排查处理机匣侧板叠面、护木下侧肋条、原厂弹匣壳、枪托表面及原厂后握把接头，更新 201 私有材质家族。分区网格与现用主体的保存范围以 `SurfaceFinish50/delivery.json` 为准，材质编译回执为 `SurfaceFinish50/materials.json`。布箱换弹由并行会话负责，本轮不修改其动作、时序、手部曲线或源码。未追加游戏测试或外观验收，不代表用户已认可 1:1 外观或 191 材质效果。

FitFinish37 的机匣/盖体几何被用户否决；ReferenceRepair38 修复横向尖刺和盖壳。HardSurface39 继续修正用户红圈中的独立脚架底座，并整理前端规则件、导轨、机匣/护木的局部平面和法线。源码存在不等于资产已接入；G43 整批回执为 `GripFinish43/delivery.json`，原厂握把沿用 J44/F50 修订，三个改装后握把以 `RearGripRestore58/delivery.json` 和当前保存资产为准。尚未获得用户整枪外观或 1:1 认可。详见 [修整与检查记录](../../Docs/Weapons/lmg201-hard-surface-20260929.md)。

Assembly40 继续修正后照门/导轨接合、右侧拉机柄外形、盖下可见内壁、原厂弹匣接口和扳机护圈；已通过已有编辑器保存，未运行游戏。详见 [本轮接合记录](../../Docs/Weapons/lmg201-assembly-20260929.md)。

用户随后指出 A40 照门仍挡住 ADS、扳机仍脱接；SightFinish41 根据实际瞄准标记下移并扩大照门开口，补齐护圈连接肩与扳机上端，并同步 201 金属表面至参考 191 的私有材质家族。已后台导入保存，完成指定视线/接合几何排查；未实机或渲染验收。详见 [当前修订记录](../../Docs/Weapons/lmg201-sight-finish-20260929.md)。

SurfaceReform42 针对两侧毛躁、脚架接头和扳机轮廓继续修整：重建左右不同的侧板凹槽/加强筋、前肩、紧固件、弧形护圈和曲线扳机，替换支腿上端粗糙接头。现用枪体与三个脚架资产均已后台保存；源文件和原资产备份保留，未追加渲染或游戏测试。详见 [表面重整记录](../../Docs/Weapons/lmg201-surface-reform-20260929.md)。

GripFinish43 补齐原厂和三种改装后握把连接肩，调整握把接触区，烘焙 86 段现用动作的右手回握修正，并升级整枪材质。该批资产已保存；201 专用预览照明的原生构建状态见 `GripFinish43/build-result.json`。未追加游戏测试或渲染验收。详见 [握把与材质记录](../../Docs/Weapons/lmg201-grip-finish-20260929.md)。

2026-09-30，GripJunction44 根据后握把专项排查替换 G43 独立通用连接座，按原厂及三种改装握把的实际截面生成连续连接颈，修复新面 UV 并统一每个握把本体／颈部的聚合物表面。枪体、三个改装握把和湿润映射共五个现用资产已后台保存。该轮三种改装握把曾使用约 4.5 万三角形；这版几何后来被否决，已由 R58 母版恢复取代。原手部动画未改动。未追加游戏测试或渲染验收。详见 [J44 修复记录](../../Docs/Weapons/lmg201-grip-junction-20260930.md)。

2026-09-30，ClothTop45 按用户要求排查布料弹箱上方粗糙原因，局部重建连续包边、布面和供弹口框，保留下半部袋身与新旧箱骨骼。已后台保存枪体、供弹分件、材质、湿润映射和选项图标，回执为 `ClothTop45/delivery.json`。未运行游戏或追加验收渲染。详见 [方案与交付](ClothTop45/README.md)。

## 保留的旧来源

Skin07/ArmSprint06 是基础动作捕获源；BeltFeed08 保留基础动作和骨架；PKMFK19 给 Accessories22 提供姿态；Refine12 仅保留原装弹匣抓握所需的 `201_surface.json`；Video26 编辑源只给 Install30 提供原生骨架。它们的旧说明与旧导入器不是当前部署入口。

不要按目录编号批量重跑历史导入脚本。已归档的首轮模型不能覆盖现用资产。Repair36 仍读取 Detail35 的加厚前脚本、Work 和贴图，不能整目录移除 Detail35。

公开 Git 保存选定作者代码、说明与归档清单；完整模型、贴图、Manny/Infima 动作、密集骨骼/网格数据及参考视频仍需本机合法来源。详见 [发布与恢复边界](../../Docs/Weapons/lmg201-publication-20260929.md)。此前归档发布未运行游戏。本轮 H39 按用户要求完成保存资产的局部几何、硬边、材质绑定和离线灰模检查，未开启 UE GUI 或运行游戏。

## 2026-10-01 发布补充

当前恢复、ClothReload44.4b 与 ArmHinge55 的叠加顺序、R58 已保存但尚未游戏验收的状态，以及 86 份废案归档见 [本轮发布记录](../../Docs/Weapons/lmg201-publication-20261001.md)。本轮仅整理与发布，没有运行游戏。
