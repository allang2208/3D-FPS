# V6 裸手、裸臂推广

用户已认可 M4 V6，授权推广到所有现有第一人称手模。本次不改第三人称 Body，不重做武器动画。

## 范围与形状

保留 M4 已认可资产；制作 AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、RuneSword、FrostSword、FrostArms、Axe、Pickaxe、Traversal，以及 DW715 / M1911 的左右单手版本，共 20 个第一人称 profile。

母版为 `OriginalShapeBareM4/BareUpperArmsV6/M4_original.json`，保留 V4 手腕收缩、手背平滑、原握持轮廓和 V6 上臂/肘部裸肤线条。各 profile 从本枪原生参考骨架迁移，保留骨骼名称、索引关系与绑定姿态；原生保留顶点沿用本枪权重，新手腕接环沿用母版插值权重。保留顶点以本枪原生坐标加形状差值，避免导入精度差异改变接触。

ASH12、M16 的参考姿态与 M4 不同，使用逐骨参考矩阵转换，不能直接替换成 M4 骨架。双持仅生成对应侧完整手臂。原枪网格、动画、武器部件和装备存档均不修改。

## 皮肤与资源

19 个新增模型位于 `/Game/Characters/ModularOutfit20260924/BareArmsFamilyV6/<Profile>/SK_<Profile>_BareArmsV6`。共享 `Materials/MI_BareFamily_Arms` 和 `MI_BareFamily_Hands`，派生自已认可 V6 全臂与 V5 手部材质。

UV0 保留解剖贴图。UV1–3 携带母版参考位置/法线，使用全精度 UV，让不同绑定姿态使用相同 8 cm 皮肤细节尺度、手腕过渡和高度场法线。没有新增贴图或运行时顶点变形，沿用现有有界高度偏移，无 POM 循环、WPO 或逐帧 CPU 形变。维持三级 LOD。

皮肤图源继续沿用母版记录：`SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/RefinedSkinV3/External/SkinHuman002/provenance.json`。

## 接入

`FPSModularOutfitComponent.cpp` 将 `fps.Outfit.BareArmsCandidate` 从 M4 专用扩为显式登记的本地第一人称 profile；保留 `bOnlyOwnerSee` 限制，不给世界武器副本添加手臂。配置中的全局 `native_bare_hands_default` 不变。

全部新资源保存后，再更新 `Content/ColdSteelData/modular_outfits.json` 中 20 个 profile 的 `bare_arms_candidate`、`native_bare_skin`、`base`。衣服遮盖 0/1 材质区，手套遮盖 2。装备原版战术手套继续走 `source_arms`，恢复各武器原生手套、袖子；脱下后恢复裸手版本。异步加载完成前保留原有显示。

## 制作文件与交付状态

- 原生导出：`Tools/ModularOutfit/export_bare_family_sources.py`。
- 离线形状迁移：`Tools/ModularOutfit/author_bare_arms_family.py`。
- 可编辑模型：`Tools/ModularOutfit/save_bare_family_blends.py`，输出 `SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Editable/`。Blender 材质为编辑预览，正式皮肤由 UE 材质定义。
- UE 导入与配置发布：`Tools/ModularOutfit/import_bare_arms_family.py`。使用项目现有批次互斥与后台 commandlet；不与打开的编辑器并行导入。
- 单资产落盘回执：同源目录 `Saved/<Profile>.json`；完整配置发布回执：`published.json`，保存原 profile 字段供恢复。

已完成 19 套新增 UE 骨骼网格及 4 个共享材质资源保存，20 个第一人称 profile 已发布。M4 继续引用原认可资产。19 份可编辑 Blend 已保存。

Native DLL 构建完成：`Saved/BuildEditor/build-20260925-012859.log`。后台导入完成：`Saved/BareArmsFamily20260925/import-commandlet.log`，commandlet 返回成功；落盘回执见上述源目录。

本次不启动游戏，不做自动测试、截图或动作验收，视觉与动作表现交由用户测试。
