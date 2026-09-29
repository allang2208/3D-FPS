# 钢甲护手：手背、腕部和拇指连续过渡

用户提供的持柄截图中，手背大甲片、斜置腕甲、袖口甲和拇指根小方片分别成块，轮廓与接缝显得错乱。本次按用户指定的视觉优先原则，允许金属过渡区随手柔和弯曲。

## 实施

- 两手各制作一张连接手背、腕部、拇指的钢质外壳。主甲保持原有宽覆盖，向后连续延伸至前臂；移除独立腕甲及它与袖口、手背之间的交叠边。
- 拇指护面与手背边缘共用顶点，经圆弧过渡延伸到拇指末节。移除原拇指根小方片、三块分离拇指甲及其小铆钉。连接处使用同一层厚度和连续表面法线。
- 腕部在原生手骨、前臂扭转骨之间平滑分配权重；虎口和拇指沿原生拇指骨链渐变。此处有意放弃整块甲片绝对刚性的约束。
- 主甲保留四颗较小铆钉。其余四指继续沿用已有逐指节甲片与小拇指范围拟合，皮革内衬和关节金属护层保留。
- 烘焙共用的 2048 px BaseColor / Normal / ORM，更新同款装备图标及掉落模型，派生到既有的 22 个原生手臂配置。

运行时继续使用原骨架、原装备定义 `ue_steel_gauntlets` 和原动作。此次不制作新动画、不修改此前的小拇指姿态修正层，也不添加逐帧求解。材质槽维持皮革、钢甲两槽，网格导入沿用已有三级 LOD。

母版生产输出为 2 张连续外壳、24 块其余四指甲片、24 颗铆钉和 2 个柔性金属护层。第一人称双手 LOD0 为 144,026 三角，单手 72,013 三角，Body 为 146,544 三角。此次将几何密度用于可变形的连接曲面；这些是制作输出计数，没有进行性能采样。

## 制作文件

- 新造型生成器：`Tools/ModularOutfit/steel_gauntlet_smooth_transition.py`。
- 母版制作、贴图、图标：`Tools/ModularOutfit/build_steel_gauntlets.py`。
- 原生骨架派生及实际导入：`derive_steel_gauntlet_family.py`、`import_steel_gauntlets.py`。
- 作者源：`SourceAssets/MetalGauntlet20260927/SteelGauntletV1/`。
- 改造前源文件、贴图、图标及制作脚本：该目录下 `SmoothTransition20260928/Before/`。
- UE 保存目录：`/Game/Characters/ModularOutfit20260924/SteelGauntletV1/`。

## 交付状态

2026-09-28 12:56（本机时间）后台 commandlet 完成实际导入和保存，退出码 0，发布标记为 `STEEL_GAUNTLETS_PUBLISHED ue_steel_gauntlets 22`。22 个骨骼网格、共用钢材贴图/材质、掉落网格及装备图标已更新，物品条目和换装配置已合并回当前数据。没有启动图形编辑器，没有 C++ 改动或新增动画。

制作日志：`Saved/steel-smooth-transition-production-20260928.log`。派生日志：`Saved/steel-smooth-transition-family-20260928.log`。实际导入日志：`Saved/steel-smooth-transition-import-20260928.log`。作者源目录内的 `saved-assets.json`、`published.json` 和 `SmoothTransition20260928/delivery.json` 记录本轮已保存产物。

本轮不启动游戏、不进行动作或穿模验收。历史小拇指接触统计对应此前的模型版本，不能作为当前连续外壳的测试结果。视觉过渡与各武器动作表现交由用户游戏内测试。
