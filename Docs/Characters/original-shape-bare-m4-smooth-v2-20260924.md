# M4 原手型裸手：平滑与毛孔 V2

用户反馈 V1 虽然改成肤色，原手套的表面痕迹仍在，要求完善平滑并借鉴地牢墙面位移细节。V1 只做一次浅层手背削平，同时冻结分片边界并保留原法线，因此未完整处理手套护垫、分片和接缝的表面表现。

## 制作内容

- 在原 M4 手模上进行六轮局部二次曲面平滑。采用局部曲面拟合，避免直接反复平均顶点造成手指整体缩小。
- 手背位移上限 1.4 mm，手指上限 0.9 mm，向接触面渐变至零。掌面、指腹、虎口、指尖端部和前臂连接位置受约束；手指不沿骨段轴向移动。
- 重建手部连续法线，UV 分片共用一致的表面方向。皮肤面不再继承原手套的硬边法线；腕臂实际接合位置渐变回原法线。
- 原拓扑、UV、骨架、绑定变换和蒙皮权重保留；前臂／衣袖位置、动画文件和原版战术手套恢复装备不改。
- 使用平滑后的法线重新烘焙解剖贴图，并降低原程序掌纹和甲缘的浮雕幅度。

## 地牢墙面方法如何用于皮肤

参考 `Docs/Gameplay/dungeon-wall-relief-followup-20260924.md` 和 `dungeon-wall-material-release-20260924.md` 的同一高度场、物理纹理尺度、共享采样坐标及距离／像素渐隐原则。

本版单独生成 2 cm × 2 cm 的皮肤微表面。毛孔直径设计为 0.13–0.28 mm，高度范围 0.025 mm。随机位置、椭圆形状与深浅变化来自确定性作者源。原始高度保留 float32 厘米数组和 16-bit 灰度 PNG，微法线与粗糙度由同一高度场生成。

UE 使用一张 1K RGBA BC7 微细节纹理，RG 为切线法线，B 为高度，A 为粗糙度。在原 UV 上按实际手部面积换算平铺尺度，两次有界采样完成极浅的高度偏移；法线和粗糙度使用同一偏移位置。掌面减弱、指甲排除，细节随像素足迹渐隐。没有照搬墙面的多步 POM，也没有使用 WPO／几何位移制造毛孔，因此毛孔本身不改变武器接触位置。

运行时不增加 Tick 或逐顶点平滑。几何处理、法线重建和解剖贴图烘焙全部离线完成。这里没有进行帧率测量。

## 作者文件和接入

作者目录：`SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/SmoothSkinV2`。

- `M4_OriginalShape_BareHands_Editable.blend`：原形态、V1 和 V2 shape key，带平滑法线及打包纹理。
- `M4_bare_shape.json`：新位置、手部角法线及原生面／顶点 ID。
- `authoring.json`：制作时记录的位移和处理数量，不是运行验收。
- `micro_surface.json`：毛孔物理尺度、编码及运行材质参数。
- `SkinPores_HeightCm.npy` / `SkinPores_Height16_Source.png`：厘米高度源和可编辑高度图。
- `skin_detail.hlsl`：有界微高度偏移、法线与粗糙度联动。

制作入口按顺序为 `author_smooth_skin_m4.py`、`bake_smooth_skin_m4.py`、Blender 中的 `author_smooth_skin_blend_m4.py`，最后经现有 UE 桥执行 `import_smooth_skin_m4.py`。均位于 `Tools/ModularOutfit`。

目标 UE 目录：`/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SmoothV2`。所有资产保存后才修改 M4 的 `bare_arms_candidate`；V1 独立保留。

仅 M4 未装备模块衣服／手套时启用，装备“原版战术手套”继续恢复原版。配置在下一次进入游戏时读取。

## 当前落盘状态

更新：用户于 2026-09-24 的截图反馈仍存在手套腕口和护垫轮廓，且皮肤细节过于平滑。本版未获视觉接受，当前 M4 候选已替换为 [V3 连续手腕与皮肤细节版](original-shape-bare-m4-refined-v3-20260924.md)。以下为 V2 当时的保存记录。

离线模型、贴图、新材质、实例和三级 LOD 网格均已制作并保存。用户结束游玩后，现有 UE 桥完成保存，回执为作者目录内的 `saved.json` 与 `import-03.txt`。M4 的 `bare_arms_candidate` 已切换至 V2；原版恢复装备和其他枪械配置保留。

未启动游戏、播放动画、截图或运行视觉／性能验收。用户当前的游玩不作为本次自动测试。
