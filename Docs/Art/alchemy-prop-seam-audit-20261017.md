# 炼药道具接缝与底部线条审计

日期：2026-10-17  
范围：药水/配料瓶、搅拌勺、长柄舀勺，以及药水工作台其余可操作器具。  
方式：Blender 5.1 离线读源 `.blend` / 导出 `.fbx`，做网格统计、BVH 互穿检测、平面色与黏土渲染。审计阶段**没有启动 UE、PIE、游戏或构建**；修复阶段只用隔离 host commandlet 导入资产，未打开可见编辑器。

## 结论

瓶底和搅拌勺上的“不明线条”**不是破面、重面或简单的平滑组错误**，最可疑的是两件事叠加：

1. **独立零件互穿**：瓶底 `reinforced bottle heel`（或红根瓶的 `root bottle heel`）与玻璃瓶身实际相交；搅拌勺的 `Stirring shaft` 与 `Oval paddle` 相交。两个实体各自完整，但没有做布尔合并、没有过渡倒角，也没有遮住接缝的箍环，所以在高光/透明玻璃下露出接缝线。
2. **硬边全按平滑着色**：瓶底的 90° 台阶、勺头的 60–100° 边缘都被标成 smooth，没有 sharp edge / 分叉法线；FBX 导出又把平滑法线烘进去，硬边就变成一条柔和的暗带或亮线。

另外，瓶身的标签/蚀刻刻度是**独立开放面片**；如果实机线条出现在瓶身侧面而不是底圈，还要单独查它们的贴面偏移和材质。它和瓶底线条不是同一类问题。

**2026-10-17 已实施修复**：BaseFluid/RedRoot 的底环已改为贴合玻璃（互穿 0），搅拌勺/长柄舀勺已加铜箍，30 个 FBX 统一做了 35° 硬边分叉；14 个交互网格和 14 个运行网格已导入并安装到原 Content 路径。详见下文“修复实施”。

**2026-10-18 更正**：用户实机截图确认，瓶底和勺头旁的细线是 **RedRoot 瓶盖的长提取管**，不是模型接缝、镭射或 hover 描边。本次模型修复属于独立的几何清理，并没有消除那条线；实际修复见 [RedRoot 瓶盖长提取管](alchemy-cap-pipette-line-fix-20261018.md)。

## 证据

### 1. 瓶底：瓶身与“加固底环”互穿

BaseFluid 源模型：

- 玻璃瓶身：`thick graduated reagent vessel`，外径约 5.6 cm，底部 z=0.25–0.53 cm。
- 底环：`reinforced bottle heel`，外径 5.76 cm，内径 **2.72 cm**，z=0.34–0.76 cm。
- 瓶身外径在底环高度处约 **2.8 cm**，底环内径比瓶身外径小 **0.08 cm**，即底环内壁嵌进玻璃里。
- BVH 三角形互穿检测：`thick graduated reagent vessel` × `reinforced bottle heel` = **720 对三角形相交**。
- 红根瓶同结构：`amber root extraction bottle` × `root bottle heel` = **720 对**。

![瓶身与底环的互穿（灰=玻璃瓶身，红=底环）](../../SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/bottle-heel-vessel.png)

灰色是瓶身，红色是底环；红色内缘就是嵌进玻璃里的那一圈。把玻璃换成半透明后，底环透过玻璃显示为瓶底的一圈红环，位置和视觉上的“不明线条”一致：

![半透明玻璃下的底环内缘（红=底环，蓝=液体）](../../SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/bottle-heel-through-glass.png)

底环本身还有上下两道 90° 硬边（z=0.34 / z=0.76），且全部 smooth。

同时确认：

- **不是液体与玻璃互穿**：`high purity fluid` × 瓶身 BVH 为 0；液体底面 z=0.55，瓶内底约 z=0.53，有 0.02 cm 间隙。
- **不是重面/z-fighting**：瓶底没有重复面、零面积面或非流形边；问题是两个实体相交，不是共面。
- 瓶底附近至少有四圈不同零件/台阶：瓶身外底 z=0.25、底环下缘 z=0.34、瓶身肩 z=0.38、瓶内底 z=0.53、液面底 z=0.55、底环上缘 z=0.76。透明材质会把其中几圈同时显示出来。

### 2. 搅拌勺：轴与勺头互穿

`SM_AlchemyStirrer` 由 `Stirring shaft` + `Oval paddle` + 四道握柄环组成：

- `Stirring shaft` 是半径 0.52 cm 的圆杆；`Oval paddle` 是一整块车削实体，圆杆直接穿过勺头。
- BVH：`Stirring shaft` × `Oval paddle` = **96 对三角形相交**。
- 勺头没有箍环/过渡套，轴与勺头在顶面形成 T 形接缝；两件都是黄铜，界面处法线不连续，实机是一条明显的接缝线。
- 勺头边缘还有两道 60°/70° 的硬边被标成 smooth（z=-23.5 / -20.2），会叠一条柔和暗带。

![搅拌勺轴与勺头（灰=杆，红=勺头）](../../SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/stirrer-shaft-paddle.png)

`SM_AlchemyLadle` 同理：长柄从勺斗上缘进入，柄/斗虽未在 BVH 上判定为相交，但交界是一圈硬边；没有箍环遮缝。

![长柄舀勺柄与斗（灰=柄，红=斗）](../../SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/ladle-handle-bowl.png)

### 3. 同类风险的资产

对全部炼药交互/运行 FBX 做了离线扫描，统计“夹角 ≥55° 但仍为 smooth”的边。数值只用于筛查，不等于全部都是缺陷；但它能说明哪些资产有同类的硬边未分叉问题：

| 资产 | 硬边仍 smooth | 底部 12% 内 | 备注 |
| --- | ---: | ---: | --- |
| `SM_AlchemyBaseFluidOpen` | 800 | 496 | 瓶身/底环/液体/标签合并体；底环互穿确认 |
| `SM_AlchemyBaseFluidCap` | 768 | 288 | 瓶盖装配体，底面硬边 |
| `SM_AlchemyRedRootOpen` | 912 | 496 | 红根瓶底环互穿确认 |
| `SM_AlchemyRedRootCap` | 1056 | 0 | 瓶盖装配体 |
| `SM_AlchemyBlueFungusOpen` | 611 | 197 | 罐体/底部台阶；有平直面混合 |
| `SM_AlchemyBlueFungusCap` | 960 | 144 | 罐盖 |
| `SM_AlchemyCatalystOpen` | 1492 | 444 | 催化瓶，底部硬边最多 |
| `SM_AlchemyCatalystCap` | 602 | 480 | 瓶盖底面 |
| `SM_AlchemyDose` | 1600 | 128 | 量瓶 + 铜颈环/刻度环，环件与玻璃相接 |
| `SM_AlchemyStirrer` | 96 | 96 | 勺头/杆互穿确认 |
| `SM_AlchemyLadle` | 128 | 0 | 柄/斗交界 |
| `SM_AlchemyPestle` | 96 | 48 | 杵头车削硬边 |
| `SM_AlchemyHourglass` | 144 | 48 | 沙漏盖/立柱装配 |
| `SM_AlchemySand` | 96 | 48 | 沙堆底部硬边 |
| `SM_AlchemyStream` | 32 | 16 | 液流圆柱上下盖硬边 |
| `SM_AlchemyLiquid` | 1984 | 128 | 锅内液面/底缘，硬边全 smooth |
| `SM_AlchemyHeater` | 2304 | 192 | 加热环装配 |
| `SM_AlchemyBody` | 34,785 | 792 | 工作台整台装配；木纹/粗糙度可能遮住，但量大 |

瓶底附近的“未知线”最可能先来自 **BaseFluid / RedRoot 的底环互穿**；BlueFungus/Catalyst 没有同样的底环命名，但底部硬边数量更高，需按各自源文件单独确认是否也有独立底环/座圈。

## 根因

### A. 先做零件，再直接 join，没有布尔/过渡

作者的 `export()` 只做 `bpy.ops.object.join()`，不合并相交体积；`bevel()` 只给单个零件加圆角，不处理两件之间的交界。因此：

- 底环内壁嵌进玻璃；
- 杆直接穿过勺头/勺斗；
- 盖子的卡环、密封圈、撕带、防滑筋互相插入（瓶盖装配体内有大量互穿，属于装配体常态，但硬边会露线）。

### B. 所有面都 smooth，没有 sharp edge

`lathe()` / `rod()` / `cylinder()` 生成的实体基本都是 `smooth=True`；`bevel()` 也只设置 `use_smooth=True` + Weighted Normal，没有按角度标记 sharp。车削轮廓的 90° 台阶、勺头 60–100° 边缘因此共享平均法线。FBX 导出使用 `mesh_smooth_type='FACE'`，导入后虽然 `has_custom_normals=True`，但那是“平滑后的法线”，不是硬边分叉。

![瓶底黏土渲染：底缘是一圈硬边](../../SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/bottle-bottom-clay.png)

### C. UV 在底部换了投影轴

`geometry.py` 的 `uv()` 按面法线主轴分 chart：瓶身侧面用 X/Y 轴，底面用 Z 轴；勺头底面和侧面也会换 chart。底圈正好是 UV chart 边界，normal map 的切线基在这里不连续，可能再叠一条细线。它不是主因，但会在“几何接缝 + 硬边”之外让线更明显。

### D. 标签/蚀刻刻度是开放面片

瓶身合并体有 37 个连通块、626 条边界边，主要来自标签和 12 个蚀刻刻度对象。这些不是瓶底线条的主因，但如果实机线条在瓶身侧面、是白色/蚀刻色，应该先查它们是否贴得太近、是否共面、是否单面。

![瓶身黏土渲染：侧面细线是标签/蚀刻刻度，不是底环](../../SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/bottle-side-clay.png)

## 修复方案

### 1. 瓶底（优先）

- **如果底环是独立橡胶/金属护圈**：让底环内表面贴合瓶身外轮廓，内径改为“瓶身外径 + 0.01–0.02 cm”，或用 Shrinkwrap/布尔差把瓶身从底环中挖掉；底环上下缘倒 0.04–0.06 cm 圆角。这样它坐在玻璃外面，而不是嵌进去。
- **如果底环本来属于玻璃**：直接把底环与瓶身布尔并集，删除内部面，交界处 0.03–0.05 cm 倒角，材质按面分配；不要保留两套内壁。
- **如果设计上就要一条环线**：把它做成真正的凹槽/凸筋（有深度、有倒角），而不是两件互相插入后留下的交线。
- 液体底面不要再作为可见圆盘：可把液体底面下移到瓶内底以下 0.02–0.03 cm 遮住，或把底面单独设为不可见；同时给液体底缘加 sharp/倒角，避免透过玻璃看到一圈暗边。

### 2. 搅拌勺/舀勺

- 优先加 **金属箍环（ferrule）**：在杆与勺头/勺斗交界处加一个 0.15–0.25 cm 高、半径略大于杆的短套，倒角 0.02–0.03 cm；既遮住 T 形接缝，也符合真实工具结构。
- 或者直接 **布尔并集** 杆 + 勺头/勺斗，交界处倒 0.03–0.05 cm 圆角；注意并集后重新计算法线，避免 ngon 阴影。
- 勺头 60–100° 边缘标记 sharp，或加 0.02–0.04 cm 倒角；不要继续全 smooth。

### 3. 法线与导出

- 在导出前统一加 **Smooth by Angle（30–40°）** 或给 ≥35–45° 的边设 `sharp_edge`，再应用 **Edge Split**（或确保 split normals 真的导出）。FBX 导出不要只用 `mesh_smooth_type='FACE'` 表达硬边。
- 车削件/杆件的端盖、底环上下缘、勺头边缘统一 0.02–0.05 cm 倒角；倒角本身用平滑，转角用 sharp。
- 修改后重新扫描：≥55° 且 smooth 的边应接近 0（只保留确实要柔和过渡的边）；非故意互穿应为 0。

### 4. 标签/刻度

- 与玻璃保持 0.01–0.02 cm 的贴面偏移，不要共面；必要时用双面材质。
- 开放面片不要参与瓶身布尔/合并；保持独立组件，避免在接缝处产生额外边界。
- 如果侧面线条仍在，优先检查 normal map 的 UV chart 边界，其次考虑 triplanar 或把标签单独用无 normal map 的材质。

### 5. 其余器具

瓶盖、量瓶（`Dose`）、研杵、沙漏、液流、锅面液体都建议走同一遍“硬边分叉 + 关键边缘倒角”；瓶盖的卡环/密封圈互穿是装配体常态，至少把外露底缘和顶缘做倒角，避免硬边暗带。

## 修复实施（2026-10-17）

已按上面的最小范围实施，没有改源 `.blend`、作者脚本、配方或 C++。

| 项目 | 结果 |
| --- | --- |
| BaseFluid 底环 | 内壁贴合玻璃，BVH 互穿 720 → **0**；外径 2.880 → **2.905 cm** |
| RedRoot 底环 | 内壁贴合玻璃，BVH 互穿 720 → **0**；外径 2.280 → **2.315 cm** |
| 搅拌勺 | 新增铜箍 z=-20.35…-19.80 cm，半径 0.76→0.67 cm，5.5 mm 高 |
| 长柄舀勺 | 新增铜箍 z=-18.40…-17.85 cm，半径 0.76→0.67 cm，5.5 mm 高 |
| 硬边 | 30 个 FBX 全部按 35° 做 Edge Split；清除源平滑自定义法线 |
| UE 安装 | 28 个静态网格（14 交互 + 14 运行）已复制回原 Content 路径 |

修复后的离线渲染：

![修复后的瓶底](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/FixedRenders/bottle_fixed_underside.png)

![修复后的搅拌勺铜箍](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/FixedRenders/stirrer_fixed_bottom.png)

![修复后的长柄舀勺铜箍](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/FixedRenders/ladle_fixed_bottom.png)

隔离 host 导入：InteractionV7 14/14、RuntimeV2 14/14，均 `assets_saved`；UV/材质按原槽名映射。Runtime host 0 error、13 warning（Body/Heater/Book 的 MikkTSpace 退化切线/近零副法线，原资产也有同类 UV 问题）。修复后 UE 尺寸核对：BaseFluid **5.81×11.33 cm**、RedRoot **4.63×8.95 cm**、Stirrer **6×6×32 cm**、Ladle **8.4×8.4×30 cm**，与原尺寸一致。

**边界**：源 `.blend` 与作者脚本未改，重新运行旧 `author_assets.py` / `author_runtime.py` 会重新生成未修复 FBX；需要移植本目录的后处理，或使用 `SeamFix20261017/Fixed/`。物品目录/世界源物品模型（`SM_Alchemy_PureBaseFluid` 等）未改；只修了交互/运行网格。没有打开可见 UE 编辑器，也没有运行 PIE、游戏、构建或视觉验收；隔离 host 的 commandlet 只负责资产导入。

完整步骤、备份和恢复方式见 `SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/README.md`。

## 验证边界

- 本轮做了 Blender 离线检查/修复、隔离 host 的资产导入和主 Content 安装；**没有打开可见 UE 编辑器，也没有 PIE、游戏、构建或视觉验收**。
- 互穿数量来自 BVH 三角形相交，是几何证据；实际画面是否显示为线还受玻璃材质、normal map、光照和 hover 描边影响。
- 如果实机线条是**金色**，还应单独检查 hover outline：它按深度/模板画外轮廓，独立底环、杆/勺头这类“凸出零件”可能在物体内部形成第二条轮廓；但根因仍是零件接缝。
- 修复后已用同一组离线渲染（瓶底仰视、勺头 3/4、勺柄/斗）比对；实际观感仍由用户在游戏/编辑器中确认。主 Content 的 28 个网格已替换，资产路径与 C++ 引用不变。

## 相关文件

- 源模型：`SourceAssets/AlchemyMaterials20261015/Authored/*.blend`、`VisualRefineV4/Authored/*.blend`
- 运行器具：`SourceAssets/PotionWorkbenchDesign20261015/RuntimeV2/Authored/PotionWorkbench_Runtime.blend`
- 导出：`InteractionV7/Export/*.fbx`、`RuntimeV2/Authored/*.fbx`
- 诊断脚本：`SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/Scripts/`（`_inspect_*`、`_scan_all.py`、`_render_*`）
- 诊断图：`SourceAssets/PotionWorkbenchDesign20261015/SeamAudit20261017/`
- 修复实施：`SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/`（`README.md`、`Before/`、`Fixed/`、`Import/`、`FixedRenders/`）


