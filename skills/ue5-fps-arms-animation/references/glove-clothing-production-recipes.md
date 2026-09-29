# 手套衣物制作配方与案例索引：2026-09-28／29

通用方法见 [高模、材质与厚度标准](glove-clothing-surface-production.md)。本页用于查当前制作入口、具体参数和已知版本边界；表格是 2026-09-29 的资产记录，不是永久参数或新的实机验收。

工程根：`D:/FPS3D/FPSGAME`。下文 `Tools/`、`SourceAssets/`、`Docs/` 和 `Content/` 相对该根。未来继续制作时以实际 `Content/ColdSteelData/modular_outfits.json` 的 `appearance_family`／资源引用、`items.json`、当前作者源为准，不直接重跑历史入口。

## 1. 当前外观家族与作者源

| 装备 | 物品 ID | 当时活动家族／作者源 |
| --- | --- | --- |
| 黑色皮革手套 | `ue_field_gloves_black` | `BlackLeatherStitchWearV4`；`SourceAssets/BlackLeatherDetail20260928/StitchWearV4/` |
| 棕色露指手套 | `ue_field_gloves` | `FingerlessDetail20260928`；`SourceAssets/GloveCompanionDetail20260928/Fingerless/` |
| 原版战术手套，已独立装备 | `ue_original_gloves` | `TacticalDetail20260928`；`SourceAssets/GloveCompanionDetail20260928/Tactical/` |
| 钢甲护手 | `ue_steel_gauntlets` | `SteelDetail20260928`；`SourceAssets/GloveCompanionDetail20260928/Steel/` |
| 灰钢锁子甲上衣 | `ue_chainmail_shirt` | `ChainmailSharedSway20260929`；保留 `ChainmailInterlace20260929` 几何／材质依赖，独立上衣槽 7 |

UE 黑色目录为 `/Game/Characters/ModularOutfit20260924/BlackLeatherStitchWearV4`。三款伴随手套目录为 `/Game/Characters/ModularOutfit20260924/GloveCompanionDetail20260928/{Fingerless,Tactical,Steel}`。锁子甲第一人称为 `/Game/Characters/ModularOutfit20260924/ChainmailSharedSway20260929`；Body、标准材质和图标仍为 `ChainmailInterlace20260929`，掉落形状仍保留初版衣身。详见 [环纹与同步摆动](chainmail-surface-and-secondary-motion.md)。

三款伴随手套从当时活动网格复制并逐槽换材质，保留原生形状、权重和 LOD，没有将百万面高模导入游戏。每款当时有 22 个 Body／武器／左右单手／攀爬／弓 profile；露指款另有 22 个皮肤＋手套组合网格。配置可能继续增加，不能把 22 写成永久上限。

## 2. 黑色 V2 → V3 → V4 的可复用变化

| 阶段 | 实际改进 | 不应退回的做法 |
| --- | --- | --- |
| V2 ReliefCuff | 变形表面共享 UV 的浅层 POM；真实外缘、端面、内壁及回折 | 只用法线假装腕口厚度；用静态世界投影贴手臂 |
| V3 TailoredSurface | 指腹／手背／织物分区；背厚内薄腕口；局部压褶、接触抛光 | 整只手统一毛绒、均匀硬圆环和全局膨胀 |
| V4 StitchWear | 有弧度的针脚、两端针孔、线槽、转角叠边、局部方向性擦痕 | 用均匀噪点充当磨损；再增加一套运行时纹理 |

V3／V4 腕背约 3.2 mm、内腕约 1.7 mm，两侧约 9–14% 局部压缩，约 25 mm 内平滑收薄；轻微轮廓不齐小于 0.5 mm。V2 内回折约 5.5 mm，V3 在继承结构上调整厚薄。新开口顶点跟随对应原生边界权重，掌心、指腹与指缝接触几何保持。

V4 线距约 2.5 mm，内部／掌面约 2.7 mm，织标约 2.0 mm；针孔深度约 0.12 mm，线体起伏约 0.12–0.17 mm。中段稍高、两端下陷，少量相邻变化与短褶皱服务于缝制结构。以上均为该款设计数值，不按数字强制生成所有新手套。

双手游戏网格维持 25,166 三角形，单手 12,583，Body 26,824，三级 LOD。V4 新作者字段离线烘焙进现有四张图，没有增加运行时纹理槽或新动画。

## 3. 当前贴图与材质配方

| 分组 | 纹理配置 | 材质与处理 |
| --- | --- | --- |
| 黑色第一人称 M4 图集 | BaseColor／ORM／Normal／Relief，4K | Cloth，局部绒面，图集浅层 POM |
| 黑色 Body | 四张 2K | 独立图集，沿实际 Body 腕口生成遮罩 |
| 露指 Shared、独立左手 | 四张 4K，各 UV 组分别制作 | Cloth，皮革与缝边绒面分区 |
| 露指 Body、战术 Body | 四张 2K | 分别烘焙，不能强套第一人称 UV |
| 战术第一人称 | 四张 4K | 浅护垫、裁片、针孔和接触粗糙度 |
| 钢甲 Plates | BaseColor／Normal／ORM，4K | Default Lit，保留金属度与方向性细纹 |
| 钢甲 Mail | 三张 1K 平铺 | Default Lit，灰色全金属衬底 |

黑色浅层材质参数为 `LeatherReliefDepthCm=0.08`、`ShortFiberFuzz=0.30`；伴随露指／战术为 `0.06`、`0.22`。黑色最终粗糙度限幅 `.48–.96`，伴随皮革放宽为 `.32–.96`，不强行把所有皮革调成同一高光。

`Relief`：R 归一高度、G 短纤维、B UV 岛安全衰减。伴随皮革把同一高模微细起伏字段映射到高度，中值约 0.5，尺度为 0.06 cm；不是从渲染颜色生成高度。

当前 `black_leather_relief.ush` 的案例约束：

- 最多 6 次粗步进＋2 次细化；最大偏移 8 个原始图集 texel；深度有上限。
- 距离 80–240 cm 衰减，`N·V` 约 .18–.40 渐入；mip 约 .75–3 时视差淡出，绒面另在较粗 mip 淡出。
- 每个图集实际三角形栅格化为岛遮罩，用岛内距离产生 3–20 texel 的渐变，写入 B。分辨率变化时同步考虑这些像素尺度。
- 近景最多约 13 次纹理查询，跳过搜索仍有 4 次；远处条件分支确实跳过搜索。
- 图集使用 Clamp；金属内衬平铺使用 Wrap。二者不能互换来解决接缝。
- 所有图保留 mip 和流送；本次 Blender 法线在 UE 翻绿，其他来源按自身约定决定。

伴随皮革高模法线／Relief 使用 Selected-to-Active，Cycles CPU，12 samples，margin 12 px；默认 cage 0.00055 m、射线距离为其 1.8 倍。颜色／ORM 通过材质字段的 Emission 输出获得，避免烘入场景光照。它们是现有脚本参数，不代表其他薄壁／指缝也能使用相同 cage。

金属内衬延续约 0.7 × 0.6 mm 的细环物理节奏；周期贴图本身可包含多个环，不能将整张 tile 的长度误当成单环长度。灰钢上衣从已有毛衣轮廓和权重派生；V2 主体使用环纹烘焙与浅层视差，每侧袖口另有 41 个实体环。当前三材质槽共享受限位移场，不运行逐环刚体或 Chaos；Body 保留普通蒙皮。

## 4. 当前高模数量只用于作者成本

| 高模母版 | 作者多边形数 | 用途 |
| --- | ---: | --- |
| 露指 Shared | 2,684,544 | 4K 高模烘焙 |
| 露指 Body | 1,130,880 | 2K 高模烘焙 |
| 露指独立左手 | 1,342,272 | 独立 UV 的 4K 烘焙 |
| 战术第一人称 | 1,124,448 | 4K 高模烘焙 |
| 战术 Body | 1,245,312 | 2K 高模烘焙 |
| 钢甲 Plates | 1,013,792 | 4K 刻槽和微起伏烘焙 |
| 金属内衬周期单元 | 65,536 | 1K 环纹浮雕烘焙 |

作者多边形可能包含四边形，不能与 UE 三角形直接等同比较。游戏面数及保留高面数的决定见 [分类预算](../../asset-model-workflow/references/geometry-budgets-by-use.md)。当前钢甲双手 144,026 三角形可保留，6–8 万仅是此前候选优化方向。

## 5. 代码与源文件入口

所有脚本位于 `Tools/ModularOutfit/`，下表用于定位职责，不是全部依次重跑的命令清单。

| 工作 | 入口 | 作用 |
| --- | --- | --- |
| 黑色厚度／图集视差基础 | `black_leather_relief_cuff.py`、`black_leather_relief_material.py`、`black_leather_relief.ush` | 袖口结构、UE 材质和自定义 HLSL |
| 黑色柔软腕口与分区 | `black_leather_tailored_surface.py`、`build_black_leather_tailored_surface.py` | V3 解剖遮罩、厚薄、抛光及烘焙 |
| 黑色当前收尾 | `black_leather_stitch_wear.py`、`build_black_leather_stitch_wear.py` | V4 针脚、针孔、磨损、高模与烘焙 |
| 黑色 V4 派生与保存 | `finish_black_leather_stitch_maps.py`、`author_black_leather_stitch_family.py`、`import_black_leather_stitch_wear.py` | 岛遮罩、原生派生、实际保存与发布 |
| 三款伴随手套 | `glove_family_detail.py`、`build_glove_family_detail.py` | 家族、UV 组、高模表面、烘焙及正式图标 |
| 三款图集与接入 | `finish_glove_family_detail_maps.py`、`import_glove_family_detail.py` | 岛衰减；复制活动网格、逐槽绑定与配置合并 |
| 钢甲连续结构 | `steel_gauntlet_smooth_transition.py`、`build_steel_gauntlets.py` | 连续手背／腕部／拇指，不是新材质统一重跑入口 |
| 钢甲原生派生 | `derive_steel_gauntlet_family.py`、`import_steel_gauntlets.py` | 已有结构的骨架派生；直接运行可能恢复旧表面引用 |
| 钢甲已有动作修正 | `solve_steel_temporal_pose.py`、`export_steel_pose_runtime.py` | 离线连续姿态求解与曲线导出；材质任务不调用 |
| 灰钢上衣初版依赖 | `export_chainmail_sources.py`、`author_chainmail_shirt.py`、`import_chainmail_shirt.py` | 取原生衣身与掉落形状，当前不可重跑覆盖新家族 |
| 锁环与实体袖口 V2 | `build_chainmail_interlace.py`、`chainmail_interlace_native.py`、`import_chainmail_interlace.py` | 周期高模烘焙、原生袖口、Body 与图标 |
| 当前共享摆动 | `build_chainmail_shared_sway.py`、`import_chainmail_shared_sway.py`、`publish_chainmail_shared_sway.py` | 同一内外层遮罩、保存 21 份第一人称派生、精确切换配方 |
| 装备图标 | `render_field_glove_icons.py`、`render_steel_gauntlet_icon.py`、`glove_icon_display.py` | 按活动家族出图，单只空手套与独立姿态 |

扫描皮革沿用项目已具备的 `Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl`。三款源目录中保留 `leather-source-metadata.json`，本轮没有新增下载。原扫描、几何、权重及采样数据的再分发遵守原授权，不能因新脚本公开就把第三方数据一起公开。

## 6. 装配和动作版本边界

当前钢甲连续外壳有意让腕部在手骨与前臂扭转骨间渐变，拇指沿其骨链软连接；其余四指仍分段。全覆盖灰钢衬底是在此后材质迭代中形成的，旧两槽名含 leather 不代表应该恢复皮革。

钢甲之前已有专用姿态层 `SteelGauntletPoseNode` 和离线曲线，不是重新制作全套动画。历史曲线覆盖部分 M4／M1911／DW715 动作，存在尚未消除的手枪局部接触；后续连续外壳和材质版本不能沿用旧零交叉计数声称动作全通过。当前材质同步保留这些动作数据，没有新增运行时求解。

战术手套当时 `appearance_family=TacticalDetail20260928`，`material` 为空，没有 `first_person_mode: source_arms`。它是独立全指手套，可与衣袖搭配；早期恢复整套原手臂的逻辑仅是历史／其他显式配方支持。

露指配方用组合皮肤网格，不隐藏露出的指尖；导入时只替换对应皮革槽。钢甲为 Mail／Plates 两槽。发布脚本读取最新物品表保留数值，只移动授权的外观引用。

## 7. 图标、回执和状态索引

黑色统一图标：`Content/ColdSteelData/Icons/BlackLeatherStitchWearV4/ue_field_gloves_black.png`。三款图标：`Content/ColdSteelData/Icons/GloveCompanionDetail20260928/`。锁子甲图标：`Content/ColdSteelData/Icons/ChainmailInterlace20260929/ue_chainmail_shirt.png`。以当前 `ue_icon` 为实际入口，历史目录不自动成为新发布目标。

图标使用单只空壳／单件衣服、生产 PBR、320×320 透明底、约 91% 填充；构图细则见 [手套图标](../../ue5-item-asset-workflow/references/glove-inventory-icons.md)。出图入口与作者源同步更新，避免换材质后装备栏仍显示旧衬底。

| 正本记录 | 查阅内容 |
| --- | --- |
| `Docs/Characters/black-leather-relief-cuff-20260928.md` | 地毯 POM 迁移、真实腕口、单位处理 |
| `Docs/Characters/black-leather-tailored-surface-v3-20260928.md` | 分区材质、背厚内薄、接触抛光 |
| `Docs/Characters/black-leather-stitch-wear-v4-20260928.md` | 针脚和磨损收尾、保存批次与现用 V4 |
| `Docs/Characters/glove-companion-detail-20260928.md` | 三款高模、逐 UV 烘焙与材质发布 |
| `Docs/Characters/steel-gauntlet-smooth-transition-20260928.md` | 视觉优先的连续结构与软权重 |
| `Docs/Characters/steel-gauntlet-articulation-plan-20260928.md` | 小拇指曲线修正范围和未解决接触 |
| `Docs/Characters/chainmail-shirt-plan-20260928.md` | 基础衣身与独立装备槽的历史依赖 |
| `Docs/Characters/chainmail-interlace-v2-20260929.md` | 交错环高模、烘焙、实体袖口与材质尺度 |
| `Docs/Characters/chainmail-shared-sway-20260929.md` | 当前内外层共享运动、后台构建与保存状态 |
| `Docs/Performance/glove-viewmodel-budget-20260928.md` | 资产读回规模、材质查询与非强制优化候选 |

各家族 `published.json` 记录保存和配置；黑色 V4 有现有编辑器互斥批次保存记录，三款伴随手套使用后台 commandlet，灰钢上衣使用当时已运行编辑器的桥。历史执行方式不是下一次必须打开编辑器的理由。

这些生产版本已保存并接入；没有在对应交付阶段启动游戏完成新一轮动作／画质／帧率验收。用户选择其方法作为后续标准，不等于全部武器和所有光照下均已测试通过。未来扩展保留这个状态边界。
