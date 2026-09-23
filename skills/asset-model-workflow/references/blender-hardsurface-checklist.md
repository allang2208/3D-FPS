# Blender 程序化硬表面建模自检与网格修复

> 正本／相关记录：`Docs/Gameplay/blast-furnace-model-20260923.md`。本文件只保留可复用技法，任务过程与数值以正本为准。

> 本文件由 `asset-model-workflow/SKILL.md` 按「复用面」拆出；入口只留触发表指针。
## 白模光滑、着色后扭曲的处理

用户要求排查时，冻结同一网格、相机和灯光，依次关闭结构法线、颜色贴图，再用常量材质比较；同时比较 raw、纹理导出与修整版本的几何。纹理导出可能包含减面，不能将前后差异全部归因于贴图。低反光材质只会弱化起伏，不修复孔洞和轮廓。法线重算、加面或提高纹理分辨率也不能保证修复形状；根据定位结果决定材质修正、局部制作或生成重抽。该诊断只在用户授权时执行，不成为默认验收。案例见 [5080 案例](5080-case.md)。

## 从零重建网格后必验硬边（2026-09-17）

把源几何按部件重建为新网格再导出（`from_pydata` 路线）时，**自定义法线的设置顺序会决定硬边存亡**：先设 `normals_split_custom_set()` 再设 `use_smooth = True`，Blender 会丢弃在平面着色网格上设的自定义法线，导出后整件变成全平滑（ASH-12 案例：源 113,832 对硬边 → 导出 0 对、最大夹角 0.0°），引擎里表现为"扭曲粗糙"而非材质问题。判据：**同一顶点上不同 loop 法线的最大夹角**，>25° 计为硬边；正确顺序是先平滑再设法线。材质与贴图换新不会修复这个损失。

## Blender 程序化硬表面建模的自检判据（2026-09-23 冶炼高炉）

用 `from_pydata` 批量堆封闭实体时，下面几条各对应一类**看不出来但会毁几何**的错误，都要在脚本里断言：

- **蝴蝶结四边形**：顶点环必须按周长顺序写 `(-,-),(+,-),(+,+),(-,+)`。用 `for sy in (-1,1) for sx in (-1,1)` 推出来的是 `(-,-),(+,-),(-,+),(+,+)`，第 1→2 条边走的是**对角线**：每个侧面四边形都成了 bowtie，三角化后两面法线正好相反。判据就是已有的"同一顶点上不同 loop 法线最大夹角"——**出现 180.0° 就是它**，不是"某个尖角"。本次基座、浇铸床、锭模、支墩全中招，渲染上表现为"基座像一块块碎平板"。
- **闭合环旋转体要复用首环**：矩形截面环（铁箍、法兰、垫圈）的剖面首尾点重合时，若给首尾各建一环顶点，结果是**几何闭合、拓扑开放**。案例：3 道铁箍＋炉冠箍＋法兰共 288 条边界边（8 个环：6×32＋2×16）。连面必须写成 `rings[(i+1) % count]`，让最后一段回到第一环；`remove_doubles` 只是事后兜底，不能替代这个写法。
- **UV 平铺尺寸逐多边形读自己材质的**：为了让布尔 `material_mode='TRANSFER'` 按索引映射材质，每个部件都挂满全部槽，于是"取 `data.materials[0]` 的 uv_meters"永远取到槽 0。本次耐火砖因此套用了砌石的 2.25 m 平铺，2 048 贴图的 13 道砖被拉成米级大白块——**贴图本身没问题，是 UV 尺度错了**。
- 布尔之后、冻结法线**之前**跑一次 `bmesh.ops.dissolve_degenerate`：精确求解器会沿切割线留零面积碎片，表现为"封闭性通过但存在退化面"。圆角修改器也会把窄补片挤塌成碎片（本次炉渣口宽 1.4 cm 的面片配 3 段圆角），所以消退化距离要留 0.05 mm 量级，并按面片宽度收窄该件的圆角段数。
- **圆角按"项目对体素块的既定做法"给**：调色板 `VoxelBuildPalette.EdgeRadiusCm = 1.4` 是 20 cm 块的 7% 圆角；Blender 侧先例 `PKMLowpoly20260922/build_mechanics.py:39` 用**角度限 35° 的 BEVEL + 3 段 + `use_clamp_overlap`**。两者合起来就是"块状砌体去锐角"的项目口径：只碰夹角超过 35° 的棱，柱面棱靠**开平滑着色**自然过渡（不要靠加段数硬顶）。几何硬边和着色硬边是两件事，先定各自的阈值再动手。
- **BaseColor 贴图按 sRGB 采样，所以脚本里必须写线性反照率**（2026-09-23 冶炼高炉）：把 sRGB 数值当线性写，铁的线性反照率只有 **0.027** —— 等于黑铁，怎么打光都没有金属感；症状极易被误读成"灯不够"而去反复调曝光。铁/钢基色线性约 0.40–0.56，锈是深色**电介质**（metallic ≈ 0.1，roughness ≈ 0.85），锻鳞介于两者之间。程序化脚本用 `albedo(r,g,b)` 显式收线性值、只在存盘时做一次线性→sRGB 编码，并把每种材质的线性均值写进回执当证据。
- 交付核对面数**不要**用 UE 的 `StaticMesh.get_num_triangles(0)`：Nanite 网格上它不是作者面数。本次源 6 420 面该调用返回 4 764；对已发布、记录为 139 062 面的方形祭坛调同一个 API 返回 2 164（差 64 倍）。把 FBX 导回 Blender 数，或直接数 FBX。
- **修订网格不要用 `AssetImportTask.replace_existing=True`**（2026-09-23 冶炼高炉）：它走 UE 的"重导"路径，会**复用资产里已存的导入设置**而不是这次给的 `FbxImportUI`。同一个脚本第二次替换时单位缩放被叠加，留下一个 **1.2 cm** 的网格（源是 120 cm），而脚本读回的 `get_bounds()` 当时也一起缩放，"自报尺寸"照样通过 —— 是独立进程读回才发现的。正确做法是**先 `EditorAssetLibrary.delete_asset` 再全新导入**；调色板存的是软对象路径，同路径重建后照常解析（本次复核 22 条条目无一丢失 mesh 引用）。并且**导入后必须断言占格尺寸**（本工程 20 cm 格的构件尺寸是存档契约），把这类静默缩放挡在注册之前。
- **要"写实"先查库，别急着程序化生成**（2026-09-23 冶炼高炉）：工程自有的 `/Game/UnrealNormandy`（Fab「Sharur's Normandy Village + PCG Plants」）带一整套 **4096 实拍 PBR**，已在体素块、丘陵地表、地牢残骸、工具材质里广泛使用。做法沿用既有先例：**新建自己的材质引用库贴图，不改源资产**。取用要点：
  - **打包语义从数据读出，不要照名字猜**：把图导成 PNG 后统计通道/目视即可判定。该库的 `RHAOM` = **R 粗糙度、G 高度、B 环境光遮蔽、A 金属度**（B 通道正好把图集干净区照成白、涂抹区照成黑）。
  - **库内没有可平铺的砖**：`T_HB_Wall4x4_*` 是废墟墙的**实拍扫描图集**（带透视、一半是拉伸涂抹），不是砖贴图。干净区裁出后**只映射一圈、不平铺**，把 u 接缝藏在构件自带的竖向拉条/装饰下；裁切位置用 AO 通道校验（涂抹区不烘焙 AO，读数接近 0），别手估。
  - `TextureExporter` 在本机没暴露，但 **`unreal.TextureExporterPNG` + `AssetExportTask` 可用**，可把库贴图导出成 PNG 做离线预览；`ImageWriteBlueprintLibrary` 也在。
- **程序化贴图脚本的两个静默零值陷阱**（2026-09-23，都被"渲染全黑"抓到）：① `Image.resize`／`thumbnail` 在 PIL 12.3.0 上对**文件来源的大图返回全零**（合成图正常、`tobytes()` 数据正确）——降采样改用 numpy 的整数倍块平均；② `with Image.open(...)` 块里 `return np.asarray(image)` 是**解码缓冲的别名视图**，块退出后内存释放，读出来全零——必须 `np.array()` 复制。判据：**贴图通道均值**（粗糙度/AO 不该是 0.000），不要只看文件大小或能否导入成功。
- **改 `get_editor_property('components')` 里某个 struct 的字段，必须把整个数组写回去**（2026-09-23 把高炉挪进"其他"栏）：`get_editor_property` 返回的是 TArray 拷贝，数组里每个 struct 也是**值拷贝**，就地 `set_editor_property` 改完字段，调色板根本不知道，`save_packages` 照常成功、mtime 照常更新，落盘的却是旧值。症状是"内存里 `is_none()` 通过了、保存后独立进程读回还是旧值"。正确做法：`components[index] = entry` 后 `palette.set_editor_property('components', components)`，再保存。另外两条：**空 FName 的 `str()` 是 `"None"`**，判断是否清空要用 `is_none()` 而不是 `str()==''`；改 USTRUCT 字段别用 Live Coding（技能已有此条，这次是在"先改再存"的路线上踩的）。
- **TextureSampleParameter2D 的 `sampler_type` 必须与贴图压缩设置一致**（2026-09-23 高炉游戏里白膜的根因）：`TC_NORMALMAP` 的贴图要求 `SAMPLERTYPE_NORMAL`，`TC_MASKS` 的贴图要求 `SAMPLERTYPE_MASKS`，`TC_DEFAULT` 的 BaseColor 才用 `SAMPLERTYPE_COLOR`。全部填 `SAMPLERTYPE_LINEAR_COLOR` 会让 `recompile_material` 报 "Sampler type is Linear Color, should be Normal/Masks"，材质编译不干净、运行时回退成无贴图的默认外观，而**资产图看起来完全正常**（槽位、贴图引用、贴图尺寸全都对）。判据：`recompile_material` 的返回列表要为空，并逐条读回 `sampler_type`（本项目枚举名写错会静默退回默认值）。另外：**commandlet 里没有渲染世界**，`RenderingLibrary.create_render_target2d`/`draw_material_to_render_target` 传 `None` 作 world context 会静默空转（日志 "A null object was passed as a world context object"），所以"把材质画到 RT 再读像素"这条离线验证路在本工程走不通，别在上面耗时间。
