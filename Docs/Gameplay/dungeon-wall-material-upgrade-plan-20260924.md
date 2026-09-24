# 地牢墙面材质检查与升级方案

日期：2026-09-24。状态：检查与方案已完成，正式材质尚未替换。

## 结论

原贴图的结构和加工方式确实是问题来源。当前材质能够显示凹凸，但“有凹凸”和“像真实水泥砂粒”是两件事：主墙表现为均匀噪点，砂浆表现为圆润团块，破损截面的扫描衍生图则存在拼块色差和重复图案。继续提高原高度图的强度，会放大这些特征。

本次直接查看了源贴图、生成脚本、编辑器内实际材质和房间模型材质槽，并使用现有 UE 编辑器对三个现用材质各拍摄了两张受控侧光近景。未启动游戏，未切换或保存地图，未保存任何生产资产。临时拍摄对象已清理。当前地图有未保存标记；拍摄前未记录地图脏状态，不能断言标记由此次操作产生，亦未清除它。

这组图片是**现用材质在临时平面上的 UE 渲染**，不是地牢实机截图。它证明这些材质在受控光照下可以输出表面变化；游戏中的灯光、实际驻留 mip 和时间抗锯齿对观感的影响仍不能据此排除。

## 实际发现

| 对象 | 本次证据 | 对观感的影响 |
| --- | --- | --- |
| 完整混凝土墙面 `M_Concrete` | 原始 BaseColor 主要是云状灰斑；生成脚本以 Noise 组合高度。UE 近景呈密集、均匀细噪点 | 缺少砂粒大小差异、稀疏气孔和局部磨损，整体像粗糙涂层；单纯加强法线会更像砂纸 |
| 剥落后砂浆 `MI_FabExposedBed` | 当前 2K 图覆盖 128cm；`noise(181)` 的格距约 7mm，`noise(251)` 约 5mm，经过平滑阈值生成团块/孔洞。格距不是精确颗粒直径。渲染可见圆润边缘、大块抹面及梳齿痕 | 特征尺度和轮廓偏大、偏软，缺少细砂断面的锐度；某些区域有蜡质、熔融感 |
| Fab 破损截面 `MI_FabBrokenConcrete` | 从原始 8K UDIM 的两块约 983×983px 区域，抽取 256px 拼块制作 1K 平铺图。原始裁片已有扫描/贴图拼接痕迹及红色残留；最终图进一步出现重复斑点和拼块色差 | 商品标称 8K 不等于当前墙面使用一张 8K 平铺材质；原模型专用图直接裁片平铺，难以得到干净连续的水泥表面 |
| 材质接入 | 当前读取的 Distribution、Threshold、Transit 共六个壳体/瓷砖模型，主墙指向 `M_Concrete`，两种砂浆槽指向当前投影 Relief 父材质；三个被检查材质无 Nanite override | 在这些已检查的资产中，没有发现仍绑定旧砂浆父材质的情况；这不是运行中每一个实例的全面审计 |
| 纹理设置 | 本次读取的混凝土颜色、法线及 Fab 颜色图均为 LODBias=0、MaxTextureSize=0；颜色 sRGB、法线压缩设置对应正常 | 没有发现这些纹理被资产级参数强制降分辨率。实际运行的流送级别仍需在后续样板中结合距离观察 |

原有 2K 主墙图若按 2m 覆盖，密度约 10.24px/cm；2K 砂浆按 128cm 覆盖，约 16px/cm。1mm 细节只占约 1–1.6 个纹素，难以稳定表达边缘和变化。这是尺寸计算，并非本次测得的游戏 mip 驻留值。

当前近景证据，光照、曝光和镜头参数一致；距离为镜头到平面的垂直距离，镜头另有横向偏移：

- [完整墙面，55cm](../../SourceAssets/DungeonWallMaterialReview20260924/Images/concrete_55cm.png)
- [砂浆，55cm](../../SourceAssets/DungeonWallMaterialReview20260924/Images/mortar_55cm.png)
- [破损截面，55cm](../../SourceAssets/DungeonWallMaterialReview20260924/Images/fab_section_55cm.png)
- [完整墙面，150cm](../../SourceAssets/DungeonWallMaterialReview20260924/Images/concrete_150cm.png)
- [砂浆，150cm](../../SourceAssets/DungeonWallMaterialReview20260924/Images/mortar_150cm.png)
- [原始 Fab 裁片 1003，原像素尺寸](../../SourceAssets/DungeonWallMaterialReview20260924/Images/fab_original_crop_1003.png)
- [原始 Fab 裁片 1001，原像素尺寸](../../SourceAssets/DungeonWallMaterialReview20260924/Images/fab_original_crop_1001.png)

![现用砂浆：圆润团块与大块抹面可见](../../SourceAssets/DungeonWallMaterialReview20260924/Images/mortar_55cm.png)

## 建议实施方案

### 1. 分开制作三种表面

- **完整墙面**：以细砂水泥抹面为底，保留冷灰、旧工业空间的色调。增加稀疏小孔、压实与磨损差异，降低满屏均匀噪点的强度。
- **瓷砖剥落后的砂浆**：改为不规则砂粒、细小孔隙和局部残胶；抹刀痕保留，但减少大面积圆润团块。颜色、法线、粗糙度、高度来自同一组表面数据，避免形状互相矛盾。
- **真正的混凝土破损截面**：继续使用用户指定的 Angled Concrete Wall Section with Heavy Damage。重新选择无红色残留、无明显贴图缝的区域；若没有足够连续区域，则使用原模型对应的局部断面重烘焙。禁止把现有 1K 拼图简单放大成 4K。

主墙扫描候选可先考察 [Poly Haven — Plastered Wall](https://polyhaven.com/a/plastered_wall)。官方提供颜色、粗糙度、AO、DX/GL 法线和位移，标注实物宽度 2m、CC0 许可。这里只完成页面信息筛选，**尚未下载、导入或认定它是最终材质**；颗粒尺度和风格需要样板确认。用户指定的 Fab 素材仍保留原有来源记录及本地使用范围。

### 2. 把大尺度变化与近景颗粒分开

采用三层结构：米级色差/潮渍，厘米级孔隙/抹面，毫米级砂粒。主纹理计划使用 2K–4K；另用共享的 1K 细节法线与粗糙度图，以约 20–40cm 的物理尺寸重复。这样 1mm 细节可获得约 2.6–5.1 个纹素，具体尺寸以新素材实物尺度为准。

微颗粒优先由法线和粗糙度共同表达；适度 POM 用于较大的浅坑与残胶层次。瓷砖边缘和深剥落断面由已有几何表达，避免将细砂放大成碎石。细节法线在一致坐标基底内进行角度校正混合，实例旋转后保持正确方向。

这一思路与 [Epic 官方 Detail Texturing 文档](https://dev.epicgames.com/documentation/unreal-engine/adding-detail-textures-to-unreal-engine-materials) 的近景叠加方法一致。文档也提醒新增纹理采样的成本，因此方案采用共享微细节、距离衰减及受限的高度步进；距离衰减改善观感，并不自动等于省掉采样。预算需在实现后根据实际编译与使用方式判断，本次不承诺帧率收益。

### 3. 先交付一段墙的候选样板

第一批只制作一段包含完整墙面、瓷砖、剥落砂浆和破损截面的通道墙。旧版和候选使用相同模型、镜头、曝光和光照，提供约 0.5m、1.5m、3m 的正面与斜侧光对照；再放回原通道灯光下提供一组对照，区分材质本身的改善与打光带来的差异。

用户认可样板后，再将材质应用到房间池、通道和 BOSS 房的对应表面，并同步导入脚本中的绑定。房间拼接、门洞、碰撞及剥落区域的几何轮廓不属于这次材质升级的修改范围。

建议视觉标准：近看能分辨不规则砂粒、小孔和层次，粗糙但不蜡、不像满屏砂纸；中距离没有明显重复团块、红色污点和拼图缝；移动时细节不明显闪烁；原通道光照下仍有可读的层次。移动观感交由用户游戏测试确认。

## 本次交付范围与记录

已完成源图检查、生成脚本定位、当前材质/模型槽读取、六张 UE 受控近景及两张原图裁片。落盘内容仅为检查脚本、图片、读取记录和此方案，没有保存或替换正式材质、模型、地图，没有修改 C++。

- [UE 拍摄记录](../../SourceAssets/DungeonWallMaterialReview20260924/Receipts/capture-state.json)
- [当前模型绑定、纹理设置及临时对象清理记录](../../SourceAssets/DungeonWallMaterialReview20260924/Receipts/current-bindings.json)
- [当前材质代码读取记录](../../SourceAssets/DungeonWallMaterialReview20260924/Receipts/context.json)
- [检查脚本](../../SourceAssets/DungeonWallMaterialReview20260924/Scripts/capture_materials.py)

实施顺序：新源图候选与尺度校准 → 一段通道墙样板 → 用户确认视觉方向 → 对应表面推广。当前停留在方案阶段。
