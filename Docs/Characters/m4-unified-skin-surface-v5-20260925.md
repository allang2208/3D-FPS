# M4 裸手 V5：连续肤质和物理皮纹尺度

用户认可 V4 腕部收形，并要求继续落实后续优化。本版实现前两项：手腕与小臂统一皮肤响应、消除原 UV 密度差造成的皮纹尺度差。掌面独立指腹细纹属于后续细化，本次未增加。

## 已认可模型的使用方式

从 `OriginalShapeBareM4WristV4/SK_M4_OriginalShape_BareHands` 直接复制 UE 网格资产，只替换前臂与手部两个材质槽。没有重建网格、重新导入 FBX、修改 UV、权重、骨架、法线、LOD 或动画。袖子槽继续引用原材质。V4 模型和材质保留。

本次可编辑几何源继续使用 `SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/WristContourV4/M4_OriginalShape_BareHands_Editable.blend`；V5 材质作者源为 `Tools/ModularOutfit/skin_surface_v5.hlsl` 与 `import_unified_skin_surface_m4.py`，不能将 V4 Blend 的旧材质预览称为 V5 预览。

## 材质实现

两处皮肤共享 0.10 散射强度、0.15 cm 平均自由程和同一散射配置；皮纹、粗糙度变化和细节颜色引用同一批已保存纹理。手腕交界以相同绑定坐标计算肤色、粗糙度及掌背过渡，逐渐接入已有手掌解剖颜色和法线。前臂材质内原布料遮罩、颜色和法线方式保留。

微细节坐标改为 8 cm 参考姿态三平面映射，绕开手掌／腕部／前臂各自的 UV 密度差。三方向投影平滑混合，曲面斜角处仍有投影缩短，因此这不等于无畸变的测地展开；解决的是原 UV 造成的 2～4 倍分区密度差。

采用 Epic 的 [Pre-Skinned Local Position／Normal](https://dev.epicgames.com/documentation/en-us/unreal-engine/vector-material-expressions-in-unreal-engine) 与顶点插值传给像素材质。细节随绑定表面运动，颜色和高度使用相同坐标。参考姿态高度梯度经当前变形表面的导数转换到切线空间，避免直接将固定坐标的法线当作动画后的法线。

保留约 0.091 mm 的源高度范围及一次有界微高度视差偏移，偏移长度上限 0.24 mm；不使用 WPO、细分或多步 POM。指甲和掌面继续采用 V4 的细节抑制遮罩，掌面抑制在腕部渐入，避免跨材质交界突然改变皮纹强度。

## 成本与素材

每像素固定三方向投影，微细节部分为 6 次高度／法线／粗糙度合并采样与 3 次颜色细节采样，比 V4 单一 UV 采样增加了材质成本。继续复用原有 2K 细节图和 4K 解剖图，没有新增高分辨率纹理或运行时 CPU 更新。未测量 GPU 时间或 FPS，不能声称性能提高。

CC0 素材来源及许可沿用 `RefinedSkinV3/External/SkinHuman002/provenance.json`；没有下载新素材。作者落盘目录为 `SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/UnifiedSkinSurfaceV5`。

## 接入与边界

目标网格：`/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SurfaceV5/SK_M4_OriginalShape_BareHands`。

先编译并保存两套材质与共同散射配置，再保存复制后的网格，全部完成后更新 `Content/ColdSteelData/modular_outfits.json` 的 M4 裸手候选引用。接入范围沿用 V4：M4 第一人称、未穿模块衣服／手套时使用，原版战术手套恢复路径不变。

实际导入结果见作者目录 `saved.json` 以及 `Saved/M4UnifiedSkin20260925/import-background-01.log`。没有启动游戏、播放动画或生成验收截图；外观和运行表现交由用户测试。

本次后台 commandlet 已执行完成，报告 0 个错误；两套父材质、实例、共同散射配置及网格均已保存，M4 配置引用已切换至 V5。首次桥接期间编辑器退出，转为后台 commandlet 后曾等待引擎 SDK 探测所需的构建锁；探测随后自行完成，没有结束其他代码构建。
