# M4 裸上臂 V6

按用户要求，将当前 M4 裸手版本的上臂及肘部衣服改为裸肤，并沿用已完成的腕部收形与 V5 皮肤方案。本版修改模型轮廓和材质，实际资产已导入、编译和保存；没有运行游戏或进行外观验收。

## 几何处理

作者基线为 `WristContourV4/M4_original.json` 和 `M4_bare_shape.json`。沿原骨架的肩—肘—腕中心线，对原袖子表面做低频径向平顺，消除密集衣褶及厚度；随后添加克制的三角肌、肱二头肌、肱三头肌与肘部轮廓。肘部使用连续弯曲中心线，小臂方向的形变在肘后 7～13 cm 平滑结束。

两侧共调整 5,787 个作者顶点，最大向内收形约 1.39 cm，最大外扩约 0.255 cm。局部表面法线随几何重新生成。保留原有顶点数量、三角形连接、UV、骨骼、绑定姿态和每顶点权重；已认可的小臂远端、手腕、手掌、手指及其原法线不在形变区域内，没有修改动画。肩部根端保留原边界，本次没有新增封口或第三人称躯干。

这些数值是制作参数及导出记录，不代表动作验收。上臂和肘部经过收形后，在具体动画中的表现仍待用户测试。

## 皮肤处理

从 V5 的 `M_M4UnifiedSkin_Forearm` 复制父材质，把皮肤覆盖输入改为常量满覆盖。原袖子与小臂两个材质槽均使用新的 `MI_M4FullBareArmSkin`，消除原布料遮罩、布料颜色及布料法线对输出的影响。手部继续直接引用 `MI_M4UnifiedSkin_Hand`。

继续使用 V5 的 8 cm 绑定姿态三平面细节、约 0.091 mm 高度范围、一次有界微视差、粗糙度变化、颜色细节与共同皮肤散射配置。没有新增 WPO、细分、纹理资源或运行时 CPU 形变逻辑。裸肤覆盖面积扩大，未测量实际 GPU 耗时。

皮肤贴图来源和许可沿用 `RefinedSkinV3/External/SkinHuman002/provenance.json`。可编辑 Blend 使用打包微细节图和近似皮肤预览材质；最终肤质以 UE 保存材质为准。

## 已保存交付

- 作者目录：`SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6`，包含几何 JSON、制作参数、可编辑 `M4_OriginalShape_BareHands_Editable.blend` 及保存回执 `saved.json`。
- UE 目录：`/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4BareArmsV6`，包含网格 `SK_M4_OriginalShape_BareHands`、父材质和材质实例。网格沿用原绑定，重新生成 3 级 LOD。
- 脚本：`Tools/ModularOutfit/author_bare_upperarms_m4.py`、`save_bare_upperarms_blend_m4.py`、`import_bare_upperarms_m4.py`。
- 导入执行记录：`Saved/M4BareUpperArms20260925/import-01.txt`，现有编辑器的串行桥接批次返回 `M4_BARE_UPPERARMS_V6_SAVED`。

仅在资产保存成功后更新 `Content/ColdSteelData/modular_outfits.json` 的 M4 裸手候选指向 V6。适用范围为 M4 第一人称、未装备模块衣服或手套；原版战术手套的恢复路径沿用现有实现，V4/V5 资产保留。其他枪械、背包、仓库、存档和第三人称服装没有接入此版本。

本次使用已经运行的编辑器完成必要导入与保存，没有新启动编辑器、游戏、PIE、截图或渲染。未做实机测试，交由用户在下一次进入游戏时测试。
