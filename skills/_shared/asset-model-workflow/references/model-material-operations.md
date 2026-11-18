> 历史制作资料，按具体问题读取；用户现行后台制作、不主动测试、不跨对话协调规则优先。以下历史自检、截图和验收步骤仅在用户明确要求时启用。

## 读图与视觉判读（2026-09-15）

- 宿主能直接看图时优先直接读取；仅宿主无法读取或用户指定外部复核时，渲染、候选图和截图用入口 `D:/FPS3D/FPSGAME/Tools/deepseek-vision.ps1` 读回文字，用法与边界见 `D:/FPS3D/FPSGAME/Docs/deepseek-vision.md`。该兼容入口走 DeepSeek Flash 图片通道；需要交叉验证时再用个人技能 `deepseek-vision-skill`（智谱 GLM-4.6V 中继）。两条路都只返回文字描述，不返回像素。
- 读图用于**定性确认和列差异**：主体是否对、朝向是否合理、文字或标签是否要改、明显缺陷是否仍在。追问细节必须重新调用一次；一张图配一个具体问题，多图合并判断会串扰。 原因：图像描述只能提供观察线索，精确尺寸和接触关系需要原始像素或几何数据。
- **定量结论不交给读图**：角度、哪端更低、是否镜像、孔洞或接缝尺寸用像素测量（掩模 bbox、底边拟合、IoU）当 ground truth。读图说“朝向反了”不足以推翻用户已认可的资产。
- 读图结果写入案例时注明使用通道与提示词。不把读图结果写成用户的视觉验收，也不写成引擎运行测试通过；最终接受与否仍由用户决定。

## 在运行中的编辑器里做资产（2026-09-16）

- **外部进程保存冲突**：编辑器加载着 `.uasset` 时，独立 commandlet/脚本宿主写同一包可能因占用失败，包装接口仍可能返回 `success=True`。修改已加载资产走当前**编辑器进程内**的 MCP/Python，处理本次保存返回和错误；不要为保存而关闭编辑器。用户明确要求落盘验收时，再按范围使用磁盘状态和独立进程读回。案例：`SourceAssets/RomanColumn20260915/README.md` 的保存事故段落。 原因：进程中的对象和磁盘包可能不同步，外部覆盖会损坏当前未保存的工作。
- 当前编辑器新建的资产可继续在该进程内引用；临时网格 handle 先保存成实际资产。跨进程读取需要先保存并使用正确包路径，不把“必须重启/另开进程才可引用”作为默认制作步骤。 原因：临时对象只存在于创建它的进程，保存后的包路径才是可恢复的资源身份。
- Vibe3D（`unreal.ModelingService`）四个坑：`append_revolve_polygon` 的半径是 **radius + 剖面 X**（剖面须回中轴才封闭）；`project_uv(Planar)` 输出**厘米级 UV**，需缩放投影器；相切堆叠件**不能 `SelfUnion`**，会裂出开放边；布尔与自并集之后要重新检查封闭性、开放边与连通体数量。 原因：几何运算有各自的输入空间和拓扑条件，相切或未闭合输入可能产生开放表面。
- 建筑构件按 **20 cm 格**对齐：分段交界、pivot 与包围盒边缘都取 20 的倍数，否则与体素件叠放错位。
- **`self_union(handle, bFillHoles, bTrimFlaps)` 的第二个布尔会毁几何**（2026-09-17）：`bTrimFlaps=True` 把凉亭半球穹顶的弧面塌成直弦（顶点 z 20→286 之间一个不剩，看起来"穹顶像圆锥"），也曾破坏矮栏杆法线出黑块。曲面构件一律用多壳重叠不并集；确需并集时传 `(False, False)`。
- **Python 的 `unreal.Rotator(...)` 构造顺序是 (roll, pitch, yaw)**，不是 C++ 的 (pitch, yaw, roll)（实测 `Rotator(10,20,30)` 读回 pitch=20 yaw=30 roll=10）；按 C++ 顺序传会把构件绕错轴（径向肋条被镜像到起拱面以下）。该旋转下局部轴：**X 沿子午线、Y 切向、Z 法线**，模板盒子要"深度在 X、宽度在 Y"。
- **旋成剖面一律用构件局部 z（0 = 底面）**：写成世界高度会让整个网格偏离 pivot，表现为"构件飘在半空 + 别处冒出一圈"。建完先读 `get_bounds()` 的本地 z 是否从 0 起，再摆场。
- **`generate_collision` 会给圆弧网格补一个超大的 sphere/sphyl/taper 形状**：穹顶因此从地面垂到穹顶、堵死整个建筑内部（玩家进不去）。壳体与环的正确口径是**清空简单碰撞 + `CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE`**（三角面即碰撞体，内部通透、子弹照常命中）；盒子类构件才用逐壳 `AlignedBoxes`。生成后**必须读回形状计数**确认。改资产后运行中的 actor 要 `set_collision_enabled(NO_COLLISION)`→`QUERY_AND_PHYSICS` 重建物理状态才会生效。
- **拆装多壳体网格用 `select_connected(handle, name, point)`**：打一个"只有目标壳体才包含"的点（圆盘的空角处），选不中即自检；`selection_bounds` 在该绑定里返回空，别用它校验选区，改用 `selection_count` + 删除后 `get_mesh_info` 的边界反推。**按 z 分带 + 半宽判断"方形"会把同宽圆盘也算进去**（Ø80 圆盘半宽同样是 40，只有对角半径 56.5 区分得出）。

## 已确认的生成器切换案例

手电在 TRELLIS 候选与本地硬表面重建后仍被用户否决，改用用户指定的混元 3D 3.1/PBR 后获游戏接入认可。参见 [战术手电案例](../../ue5-weapon-workflow/references/tactical-devices.md)。不要把这一次选择升级为所有资产的默认生成器；保留新旧来源、最终母版及材质分区。 原因：作者母版与运行网格承担不同用途，保留母版才能重做细节、烘焙和距离档位。

## 白模光滑、着色后扭曲的处理

用户要求排查时，冻结同一网格、相机和灯光，依次关闭结构法线、颜色贴图，再用常量材质比较；同时比较 raw、纹理导出与修整版本的几何。纹理导出可能包含减面，不能将前后差异全部归因于贴图。低反光材质只会弱化起伏，不修复孔洞和轮廓。法线重算、加面或提高纹理分辨率也不能保证修复形状；根据定位结果决定材质修正、局部制作或生成重抽。该诊断只在用户授权时执行，不成为默认验收。案例见 [5080 案例](../references/5080-case.md)。 原因：成本取决于实际可见量与变形和材质路径，统一面数阈值会损伤近景质量。


## 从零重建网格的硬边处理与按需检查（2026-09-17）

把源几何按部件重建为新网格再导出（`from_pydata` 路线）时，**自定义法线的设置顺序会决定硬边存亡**：先设 `normals_split_custom_set()` 再设 `use_smooth = True`，Blender 会丢弃在平面着色网格上设的自定义法线，导出后整件变成全平滑（ASH-12 案例：源 113,832 对硬边 → 导出 0 对、最大夹角 0.0°），引擎里表现为"扭曲粗糙"而非材质问题。判据：**同一顶点上不同 loop 法线的最大夹角**，>25° 计为硬边；正确顺序是先平滑再设法线。材质与贴图换新不会修复这个损失。

## Blender 程序化硬表面建模的检查参考（仅用户要求时）（2026-09-23 冶炼高炉）

用 `from_pydata` 批量堆封闭实体时，下面几条各对应一类**看不出来但会毁几何**的错误，都要在脚本里断言：

- **蝴蝶结四边形**：顶点环必须按周长顺序写 `(-,-),(+,-),(+,+),(-,+)`。用 `for sy in (-1,1) for sx in (-1,1)` 推出来的是 `(-,-),(+,-),(-,+),(+,+)`，第 1→2 条边走的是**对角线**：每个侧面四边形都成了 bowtie，三角化后两面法线正好相反。判据就是已有的"同一顶点上不同 loop 法线最大夹角"——**出现 180.0° 就是它**，不是"某个尖角"。本次基座、浇铸床、锭模、支墩全中招，渲染上表现为"基座像一块块碎平板"。
- **闭合环旋转体要复用首环**：矩形截面环（铁箍、法兰、垫圈）的剖面首尾点重合时，若给首尾各建一环顶点，结果是**几何闭合、拓扑开放**。案例：3 道铁箍＋炉冠箍＋法兰共 288 条边界边（8 个环：6×32＋2×16）。连面必须写成 `rings[(i+1) % count]`，让最后一段回到第一环；`remove_doubles` 只是事后兜底，不能替代这个写法。
- **UV 平铺尺寸逐多边形读自己材质的**：为了让布尔 `material_mode='TRANSFER'` 按索引映射材质，每个部件都挂满全部槽，于是"取 `data.materials[0]` 的 uv_meters"永远取到槽 0。本次耐火砖因此套用了砌石的 2.25 m 平铺，2 048 贴图的 13 道砖被拉成米级大白块——**贴图本身没问题，是 UV 尺度错了**。
- 布尔之后、冻结法线**之前**跑一次 `bmesh.ops.dissolve_degenerate`：精确求解器会沿切割线留零面积碎片，表现为"封闭性通过但存在退化面"。圆角修改器也会把窄补片挤塌成碎片（本次炉渣口宽 1.4 cm 的面片配 3 段圆角），所以消退化距离要留 0.05 mm 量级，并按面片宽度收窄该件的圆角段数。
- **圆角按"项目对体素块的既定做法"给**：调色板 `VoxelBuildPalette.EdgeRadiusCm = 1.4` 是 20 cm 块的 7% 圆角；Blender 侧先例 `PKMLowpoly20260922/build_mechanics.py:39` 用**角度限 35° 的 BEVEL + 3 段 + `use_clamp_overlap`**。两者合起来就是"块状砌体去锐角"的项目口径：只碰夹角超过 35° 的棱，柱面棱靠**开平滑着色**自然过渡（不要靠加段数硬顶）。几何硬边和着色硬边是两件事，先定各自的阈值再动手。 原因：动作切换期间同时存在两个姿态来源，不连续的交接会造成跳变或接触滑移。
- **BaseColor 贴图按 sRGB 采样，所以脚本里必须写线性反照率**（2026-09-23 冶炼高炉）：把 sRGB 数值当线性写，铁的线性反照率只有 **0.027** —— 等于黑铁，怎么打光都没有金属感；症状极易被误读成"灯不够"而去反复调曝光。铁/钢基色线性约 0.40–0.56，锈是深色**电介质**（metallic ≈ 0.1，roughness ≈ 0.85），锻鳞介于两者之间。程序化脚本用 `albedo(r,g,b)` 显式收线性值、只在存盘时做一次线性→sRGB 编码，并把每种材质的线性均值写进回执当证据。
- 交付核对面数**不要**用 UE 的 `StaticMesh.get_num_triangles(0)`：Nanite 网格上它不是作者面数。本次源 6 420 面该调用返回 4 764；对已发布、记录为 139 062 面的方形祭坛调同一个 API 返回 2 164（差 64 倍）。把 FBX 导回 Blender 数，或直接数 FBX。
- **修订网格不要用 `AssetImportTask.replace_existing=True`**（2026-09-23 冶炼高炉）：它走 UE 的"重导"路径，会**复用资产里已存的导入设置**而不是这次给的 `FbxImportUI`。同一个脚本第二次替换时单位缩放被叠加，留下一个 **1.2 cm** 的网格（源是 120 cm），而脚本读回的 `get_bounds()` 当时也一起缩放，"自报尺寸"照样通过 —— 是独立进程读回才发现的。正确做法是**先 `EditorAssetLibrary.delete_asset` 再全新导入**；调色板存的是软对象路径，同路径重建后照常解析（本次复核 22 条条目无一丢失 mesh 引用）。并且**导入后必须断言占格尺寸**（本工程 20 cm 格的构件尺寸是存档契约），把这类静默缩放挡在注册之前。
- **要"写实"先查库，别急着程序化生成**（2026-09-23 冶炼高炉）：工程自有的 `/Game/UnrealNormandy`（Fab「Sharur's Normandy Village + PCG Plants」）带一整套 **4096 实拍 PBR**，已在体素块、丘陵地表、地牢残骸、工具材质里广泛使用。做法沿用既有先例：**新建自己的材质引用库贴图，不改源资产**。取用要点：
  - **打包语义从数据读出，不要照名字猜**：把图导成 PNG 后统计通道/目视即可判定。该库的 `RHAOM` = **R 粗糙度、G 高度、B 环境光遮蔽、A 金属度**（B 通道正好把图集干净区照成白、涂抹区照成黑）。 原因：图标显示取决于可见轮廓和容器比例，重复边框或留白会缩小有效识别区域。
  - **库内没有可平铺的砖**：`T_HB_Wall4x4_*` 是废墟墙的**实拍扫描图集**（带透视、一半是拉伸涂抹），不是砖贴图。干净区裁出后**只映射一圈、不平铺**，把 u 接缝藏在构件自带的竖向拉条/装饰下；裁切位置用 AO 通道校验（涂抹区不烘焙 AO，读数接近 0），别手估。
  - `TextureExporter` 在本机没暴露，但 **`unreal.TextureExporterPNG` + `AssetExportTask` 可用**，可把库贴图导出成 PNG 做离线预览；`ImageWriteBlueprintLibrary` 也在。
- **程序化贴图脚本的两个静默零值陷阱**（2026-09-23，都被"渲染全黑"抓到）：① `Image.resize`／`thumbnail` 在 PIL 12.3.0 上对**文件来源的大图返回全零**（合成图正常、`tobytes()` 数据正确）——降采样改用 numpy 的整数倍块平均；② `with Image.open(...)` 块里 `return np.asarray(image)` 是**解码缓冲的别名视图**，块退出后内存释放，读出来全零——必须 `np.array()` 复制。判据：**贴图通道均值**（粗糙度/AO 不该是 0.000），不要只看文件大小或能否导入成功。 原因：可读取文件与持有有效像素缓冲是不同状态，错误的缓冲生命周期会得到空纹理。
- **改 `get_editor_property('components')` 里某个 struct 的字段，必须把整个数组写回去**（2026-09-23 把高炉挪进"其他"栏）：`get_editor_property` 返回的是 TArray 拷贝，数组里每个 struct 也是**值拷贝**，就地 `set_editor_property` 改完字段，调色板根本不知道，`save_packages` 照常成功、mtime 照常更新，落盘的却是旧值。症状是"内存里 `is_none()` 通过了、保存后独立进程读回还是旧值"。正确做法：`components[index] = entry` 后 `palette.set_editor_property('components', components)`，再保存。另外两条：**空 FName 的 `str()` 是 `"None"`**，判断是否清空要用 `is_none()` 而不是 `str()==''`；改 USTRUCT 字段别用 Live Coding（技能已有此条，这次是在"先改再存"的路线上踩的）。
- **TextureSampleParameter2D 的 `sampler_type` 必须与贴图压缩设置一致**（2026-09-23 高炉游戏里白膜的根因）：`TC_NORMALMAP` 的贴图要求 `SAMPLERTYPE_NORMAL`，`TC_MASKS` 的贴图要求 `SAMPLERTYPE_MASKS`，`TC_DEFAULT` 的 BaseColor 才用 `SAMPLERTYPE_COLOR`。全部填 `SAMPLERTYPE_LINEAR_COLOR` 会让 `recompile_material` 报 "Sampler type is Linear Color, should be Normal/Masks"，材质编译不干净、运行时回退成无贴图的默认外观，而**资产图看起来完全正常**（槽位、贴图引用、贴图尺寸全都对）。判据：`recompile_material` 的返回列表要为空，并逐条读回 `sampler_type`（本项目枚举名写错会静默退回默认值）。另外：**commandlet 里没有渲染世界**，`RenderingLibrary.create_render_target2d`/`draw_material_to_render_target` 传 `None` 作 world context 会静默空转（日志 "A null object was passed as a world context object"），所以"把材质画到 RT 再读像素"这条离线验证路在本工程走不通，别在上面耗时间。

## 缩放已有网格到目标尺寸（不重建几何，2026-09-18）

需要把**别人给好的模型**改成工程尺寸（例如把包里 24.8 × 114 × 212 的门框改成 40 × 100 × 200）时，不要重做几何： 原因：尺寸调整可以沿用已有几何与绑定，重建主体会引入与缩放需求无关的变化。

1. 走 GeometryScript 原生路线：`GeometryScript_AssetUtils.copy_mesh_from_static_mesh` →
   `GeometryScript_MeshTransforms.scale_mesh(dm, Vector(sx, sy, sz), Vector(0,0,0), True)`（**支持逐轴**）→
   `copy_mesh_to_static_mesh`。先例 `SourceAssets/RomanFountain20260917/scale_fountain_2x_20260918.py`（2× 等比）。
2. **必须保留材质槽**：`copy_mesh_to_static_mesh` 默认只留**一个空槽**。包里 `SM_Door` 原本 `[M_Door, M_Glass]`
   两槽（门扇自带小窗＝半透明），并成空槽后玻璃就没了——这是用户可见的回归。烘焙后**核对 `slots` 数与源一致**
   （喷泉脚本校验过 `materials_kept == 2`，门那次漏了才出的问题）；必要时把源资产 `static_materials` 逐槽拷回。 原因：槽位索引和显示名称可能变化，语义对应错误会把材质绑定到别的部件。
3. **碰撞要重做**：缩放后旧的简单碰撞（`box_elems`／`convex_elems`…）已过期。环状／薄壳（门框、穹顶）必须
   清空简单碰撞并设 `CTF_USE_COMPLEX_AS_SIMPLE`（三角面即碰撞体）——包成盒会把门洞／内部空间堵死。
4. **pivot 不会跟着变**：包里网格的 pivot 常在边上或底边，缩放后照旧。所以摆放、预览与离线渲染一律按**包围盒**算；
   离线渲染脚本要先把网格平移到"Actor 口径"（包围盒 X／Y 居中、底面 z=0），否则会出现"门板飘到半空"这种假故障。
5. **只改尺寸就别动代码**：Actor 侧若本来就按包围盒摆位（本工程的门线就是这样），缩放后一行都不用改。
   改动顺序是"网格 → 渲染 → 进游戏只验能放能开 → 再谈代码"，越界改代码就是 2026-09-18 那次整轮回退的原因。
6. 默认完成模型导出、引擎导入和保存；用户明确要求渲染或读回检查时，再生成相应证据。需要确认落盘数据时使用独立进程读回。原因：内存中的对象不等于重新加载的包，但额外预览和检查不属于默认制作授权。
7. **逐轴缩放要挑轴**（2026-09-18 门框／门扇第二轮）：目标只有一轴不同就只缩那一轴（单扇门框 24.84 → **40**
   只缩 X）；缩"别人模型"时还要看清哪一轴是**功能尺寸**——门扇的 X 是名义板厚，跟着缩放会让铰链深度失配
   （把 5 cm 厚的门扇拉成 29.8 cm），那一轴必须保持原值，只缩洞口方向的 Y／Z。
8. **容器用 `duplicate_asset`**：本版 Python 里没有 `unreal.StaticMeshFactoryNew`，`create_asset` 建不出静态网格；
   先复制一份**源资产**当容器（材质槽一并带过来）再 `copy_mesh_to_static_mesh` 覆盖几何，比烘完再补槽更省事。
9. **包围盒原点要按消费者要求归一**：缩放不改 pivot，但如果下游是按"包围盒中心＝原点"写公式的（本工程门窗 Actor 给
   "转 180° 的那一扇"算 Y 偏移就是这样），原点偏 (0,−45,+100) 的包模型缩放后必须**平移把包围盒中心放回原点**，
   否则那件会整体偏半个身位。归零后要读回 `origin≈(0,0,0)` 当证据。
10. **"同步调整"先定基准尺寸**：用户说"门和门框一起调"时，把**外廓**缩到目标（单扇门框做成 40 × 114 × **220**，
    220 ＝ 11 格），跟着一起动的**门板**套同一个比例（220/212 → 207.55）而不是取整——包里洞口本来就＝门板尺寸，
    同比例才不会出现"门框变大、门板边上留缝"。自建框则直接取"洞口 − 缝"。
11. **烘完必须确认真的落盘**：`save_loaded_asset` / `save_packages` 会因**别的 Unreal 进程占着包**而静默失败
    （日志里是 `Error moving … to temp directory (Error Code 32)`＋`Error saving`），此时脚本的"读回"只是内存值。
    重跑前先确认没有其它 UnrealEditor/UnrealEditor-Cmd 在跑，重跑后核对 `.uasset` 的 mtime／大小确实变了。
12. **可调尺寸只留一处**：同一批资产被反复调尺寸（门高 2.2 m → 2.4 m）时，把**资产名去掉可调尺寸**
    （`…_D40` 只标进深）、脚本里只留**一个常量**（高度），下游（调色板占格／缩略图网格）改成**从包围盒算**
    而不是写死数字——这样下一次调尺寸只改一个常量重跑，C++ 与注册脚本都不用动。被取代的旧资产移入
    `trash/<task>/` 并记录原路径、大小、SHA-256 与保留替代物。

## 用 Python 造材质／材质实例（2026-09-18 喷泉水体，实战踩坑表）

2026-09-19 边缘溢流 V7 制作补充：
- 显式流向数据可用 `GeometryScriptSimpleMeshBuffers` 的 UV0/UV1，经 `append_buffers_to_mesh` 写入；UV1 存层号/时间时，关闭自动光照 UV 并启用全精度 UV，避免重建覆盖数据。
- 命令行制作中 `get_editor_subsystem` 可能返回 None；此时才用 `new_object` 创建所需编辑器子系统。
- Niagara HLSL 输入解析器可能将 `Particles.UniqueID%4` 当作变量名；本次改用 `fmod(float(Particles.UniqueID),4.0)` 完成资产编译。
- 资产完成标记应在整套内容写入、必要编译与保存完成后设置，避免中断后把空白副本当成成品。
- 制作计数和粒子预算不等于实机性能结果；测试与截图只按用户明确要求执行。

V8 自然随机性续篇：环状水帘用周期噪声保证环向接缝连续，以 `时间 - 飞行时间` 传播疏密变化；
慢变化管水束，快变化管碎边，各层/实例使用不同偏移。粒子随机初始条件应在出生时保存，更新时只推进轨迹。
Niagara 的发射器脚本仍走 CPU VM，即使粒子设为 GPU；本机 VM 不支持 HLSL `smoothstep`，
平滑插值改写为 `t*t*(3-2*t)`（先保证 t 在 0–1）。实例预算不因新增随机性而放宽。 原因：出生时固定随机初值可使轨迹连续；周期噪声闭合环向接缝，分层频率产生不同尺度的变化，兼容表达式与原实例预算保留可执行范围。

项目里已经有一套成熟的"无头 Python 造材质"路线（先例 `Tools/Building/create_voxel_assets.py`、
`Tools/ZombieDog/install_random_wounds.py`、`Tools/Building/create_build_preview.py`）。喷泉那轮又补了几条：

1. **`create_asset` 要工厂实例**：`TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())`
   —— 传**类**会报 `Cannot nativize 'MaterialFactoryNew' as 'Factory'`；材质实例用
   `unreal.MaterialInstanceConstantFactoryNew()`。顺带：本版 Python **没有** `unreal.StaticMeshFactoryNew`
   （静态网格容器要靠 `duplicate_asset` 复制一份源资产）。
2. **引脚名**：`MaterialExpressionTextureSample[Parameter2D]` 的 UV 输入叫 **`UVs`**（不是 `UV`）；
   `MaterialExpressionClamp` 的输入是**默认名**（`""`）；`Multiply/Add` 用 `A/B`，`LinearInterpolate` 用
   `A/B/Alpha`，`Power` 用 `Base/Exp`，`Fresnel` 用 `ExponentIn/BaseReflectFractionIn/Normal`，
   纹理采样节点取单通道用输出名 `"R"`。连错时 `connect_material_expressions` 返回 False **但不抛异常**——
   必须逐条检查返回值，否则会得到一个"能编译但没接对"的材质。
3. **`recompile_material` 返回的是错误列表**：`[]` ＝ 编译通过；`bool([])` 是 False，别拿它当 bool 判。
   结构自证可以用 `get_material_expressions().Num()` 加上
   `get_material_property_input_node(mat, MP_EMISSIVE_COLOR / MP_OPACITY)` 看输出挂在哪个节点上。
4. **`FCustomInput` 没有 `input_type`**（5.8 会报 `Failed to find property 'input_type'`）：
   Custom 节点的输入类型**跟着接入的表达式走**，只设 `input_name` 即可。
5. **特效网格不要依赖网格 UV**：本工程网格走 XAtlas，UV 方向不可控。水膜/泡沫/水帘这类"要按方向滚动"的材质，
   使用作者明确写入的流向 UV，或从逐像素位置自算柱面 UV。`WorldPosition − ObjectPositionWS`
   只去掉平移，不是旋转后的物体局部坐标；需要随构件旋转/缩放时用 World→Local 变换。
   **不可直接拿 ObjectPositionWS 算花纹**：它是每个物体的常量，会让所有像素采到同一点。
6. **实例参数写不进去也别慌**：`set_material_instance_scalar/vector/texture_parameter_value` 在 5.8 常返回 False
   但**实际写成功**（ZombieDog 那轮已记）；判断依据是 `scalar_parameter_values / vector_parameter_values /
   texture_parameter_values` 里出现的覆盖项名字与数量，把这份清单打进日志，用户才能知道有哪些旋钮可调。
7. **无头 commandlet 里没有关卡编辑器状态**：`LevelEditorSubsystem.is_in_play_in_editor()` 会
   `ACCESS_VIOLATION` 崩进程（喷泉那轮又踩一次）；无头脚本用环境变量护栏跳过 PIE 查询，
   加载关卡用 `LevelEditorSubsystem.load_level()` 是安全的。
8. **材质已被引用时不要重建它的表达式表**（2026-09-18 喷泉水面 v6，崩了两次）：
   `MaterialEditingLibrary.delete_all_material_expressions(mat)` 对**已被已保存的网格/材质实例引用**的材质
   会断言 `!IsRooted()`（`UObjectBaseUtility.h:209`）并直接杀掉进程。规矩： 原因：材质图可能被现有资产和渲染资源引用，局部参数修改与重建整张图的影响范围不同。
   - 常态化做法是**只改材质实例参数**（`set_material_instance_*` + `update_material_instance`），图不动； 原因：材质图可能被现有资产和渲染资源引用，局部参数修改与重建整张图的影响范围不同。
   - 非要改图：先删掉引用它的实例（并把网格槽指过去之前不要保存），或**换一个新的材质资产名**再建； 原因：材质图可能被现有资产和渲染资源引用，局部参数修改与重建整张图的影响范围不同。
   - 脚本里写成"已存在且有表达式 → 跳过重建并打印提示"，就不会因为重跑而崩。
9. **别用 PowerShell 的 `Set-Content`/`Out-File` 改写源文件**：PS 5.1 会加 UTF-8 BOM、换行也可能被改，
   中文注释在 `Select-String` 默认编码下还会显示成乱码（看起来像文件坏了，其实只是读法）。只读检查用
   `-Encoding UTF8` 或 Python `open(..., encoding="utf-8")` 读；真要改文本走 `apply_patch`。
10. **XAtlas 网格上的法线扰动可能完全无效**：切线空间法线依赖网格切线基，而切线基来自 **UV 梯度**；
    本工程网格走 XAtlas（岛方向随机、局部可能退化）→ 算好的涟漪法线被乱掉的切线基转掉，
    观感就是"一块没起伏的平板"。**水平面（水面、地面贴花）改用世界空间法线**：
    `mat.set_editor_property("tangent_space_normal", False)`，材质里直接给 `(x, y, 1)` 这种向上法线。
    一个属性解决，不改图、不依赖 UV。
11. **"动感"不要只靠一张贴图**：贴图偏平时滚动几乎看不见。确定可见的做法是
    **程序化条纹（sin 波）+ 贴图**叠加，滚动方向由自算柱面 UV 的 v 决定；
    要改已投产材质的图时**新建一个资产名**（重建被网格引用的材质会断言 `!IsRooted` 崩进程）。 原因：可见运动需要可辨识的空间变化，只有均匀颜色的贴图即使滚动也很难表现流动。
12. **拿现成材质当"底板／衬底"前先查 blend mode**（2026-09-18 喷泉"像固体"真凶）：
    包内 `M_Caustics` 是 **`BLEND_OPAQUE`**，拿它垫在盆底＝每个盆一块**不透明平板**，
    透过半透明水看下去就是"实心地板"——**水面波浪做得再好也改不了盆底的读感**。
    要"只加光"就自己做 **ADDITIVE + Unlit** 的材质（把花纹只接到 Emissive），
    让下面的实体表面照常可见；参数名与原实例保持一致，旧覆盖项才能继续生效。
13. **诊断顺序：先证明"运行态用的是哪套资产"，再谈调参**：
    ① 只读探针读资产属性（blend / shading / TLM / tangent_space_normal / WPO 与 Normal 接在哪个节点 / 参数默认值），
       并且**设完立刻读回**（本版枚举名写错会静默退回默认值）；
    ② 读 `Saved/Logs/*.log` 证明那次 PIE 进的是哪张图、编译了哪些系统、用的是哪次烘的资产；
    ③ 读 `Saved/SaveGames/*.sav` 证明玩家**有没有摆过**该构件（本例据此排除了"旧构件干盆"假设）；
    ④ 给构件加**运行期一次性日志**（组件 / 网格 / 槽 0 材质 / 可见性），一条日志定性"到底渲染了什么"。
    这四步比"再猜一轮参数"快得多 —— 本例连续 5 轮盲调没解决，靠 ① 立刻定位到不透明衬底。
14. **`MaterialExpressionObjectPositionWS` 是"物体原点"常量，不是逐像素位置**（2026-09-19 喷泉水体
    v5–v10 六轮"像固体"的**唯一根因**）：拿它当 Custom 节点的位置输入，波高场/法线/柱面 UV 全部在
    **常量点**求值 → 水面整体刚性升降（看不见）、法线均匀倾斜（无明暗变化）、水帘条纹与泡沫/焦散
    采样单一 texel（平板/隐形）。**`WorldPosition − ObjectPositionWS`**（Subtract 节点）是去平移的逐像素坐标，
    并未去除旋转/缩放；真正局部坐标应使用 World→Local 变换。判别法：隐藏水面网格拍一张 + 把 WaveHeight 调 3 倍拍一张，若轮廓/明暗
    都不变即命中此坑（参数读回全对也照样命中）。
15. **编辑器模式（非 PIE）关卡里没有太阳/天空**：昼夜是运行时 BP（如 `BP_FPS_DayNightManager`）在
    BeginPlay 生成的，编辑器视口/SceneCapture 拍出来是**夜景黑地**。实拍自检前先临时 spawn
    `DirectionalLight`(intensity 10–30) + `SkyAtmosphere` + `SkyLight(real_time_capture=True)`，
    拍完销毁、**不存关卡**。SceneCapture 配方（5.8 远程通道实测）：
    `RenderingLibrary.create_render_target2d(world,w,h,RTF_RGBA8_SRGB)` →
    `comp.set_editor_property("texture_target"/"capture_source"(SCS_FINAL_COLOR_LDR)/"fov_angle")` →
    每视角 `set_actor_transform(Transform(loc, look_at 四元数), False, True)` + `capture_scene()`×4 →
    `RenderingLibrary.export_render_target(world, rt, dir, name)`（**产物无扩展名**，要自己补 .png；
    Niagara 在编辑器 capture 里不 tick，水柱/粒子拍不到）。
16. **PIE 进行中远程脚本会静默早退**：脚本开头的 `is_in_play_in_editor()` 护栏 raise SystemExit(0)，
    表现为"success=True 但零输出零产物"；先等 PIE 结束（日志里出现 TRAVERSAL/输入行 = 正在 PIE）。
    另外**编辑器启动未完全就绪时**往远程通道发"重建材质"类命令会触发 MaterialEditor 的
    `!IsRooted()` 断言崩进程——等 `Engine Initialization) Total time` 日志后再发。
17. **滚动纹理的方向与"复制感"（2026-09-19 喷泉水帘）**：①柱面 UV 取 `v = −P.z/S` 时，
    `uv + (0,T)` 是**向上**流（特征点 z = S·(T−c) 递增）；要向下，所有含 T 的相位写成
    `(u·a + v·b − T·c)` 且 b,c>0。**验证法**：FlowSpeed 临时调到"3 s 位移 < 图案半周期"（如 0.05），
    同机位间隔 3 s 拍两张，离线对目标带做垂直互相关取 argmax dy（dy>0 = 下移）；正常速度下间隔太大
    会**混叠**得 dy=0 假阴性。②"几乎一模一样"的两个来源：纯 `sin(u·N)`（N 整数）绕圈精确复制、
    贴图整数平铺同理 → 用**非整数列尺度**采样噪声/贴图（唯一缝落在背面子午线）+ 逐列噪声调制
    相位/宽度/亮度。③重构材质图时**逐条核对每个算出来的场是否真接到了输出**（V4/V5 的 streak
    算了没接，画面只剩泡沫层读作平板）——`get_material_property_input_node` 只能查末级，
    中间场要顺着 Multiply/Add 链走一遍。
18. **归档前复核引用别用 `grep "名字."`**：uasset 导入表里的父级/槽引用不带尾点，会漏判
    （2026-09-19 把活跃的 `M_FountainWaterFilmV2` 当废案移进 trash 一次，靠 MIC 包字节扫描发现后恢复）。
    正确做法：扫候选资产包字节里的名字表（`re.findall(rb'M_名字[A-Za-z0-9_]*', bytes)`）或直接读
    MIC 的 `parent` 属性 / 网格的 `get_material(i)`；移完再列一遍 Materials 目录对账"应保留清单"。

## Vibe3D 规则几何与后处理入口（2026-09-19）

用户已同意纳入 Vibe3D。尺寸/结构明确的建筑模块、道具和机械零件优先考虑在 UE 内直接制作；已有模型按任务需要做局部几何、UV、烘焙、碰撞与 LOD。此分支已有充分参考和尺寸时不强制生成三视图或跑 5080；图生模型继续沿用用户指定生成器与选中母版。细节见 [Vibe3D 制作与后处理](../references/vibe3d-workflow.md)。动画、玩法及存档继续接续对应领域技能；默认不测试、不截图、不启动 PIE。 原因：用户认可的是具体母版和观感，换成另一版本会改变已有接触或外观基线。

## 已退役的生成枪体案例：PKM（2026-09-22）

本次 PKM 从生成候选到多轮拆分、材质和动作接入均被用户列为废案，归档留存不代表可自动恢复。见 [生成枪械失败边界](../../ue5-weapon-workflow/references/generated-rifle-refinement.md#失败案例pkm-全系列已退役2026-09-22)：保留原模型身份；连通岛/空间分区不等于机械零件；几何、法线、材质和导入原因分别判定。此次失败不能据以宣布 Meshy 管线上限，也不能将没有视觉认可的后续算法写成成功经验。
