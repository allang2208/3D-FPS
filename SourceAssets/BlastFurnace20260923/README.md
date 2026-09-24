# 冶炼高炉（矿石 → 锭）：Blender 建模与接入

2026-09-23。对应 [玩法路线图 O2 野外设施模型](../Gameplay/gameplay-roadmap-20260918.md) 与
[Backlog O2](../Backlog.md) 里"高炉本体模型"这一项。本次只做**世界模型本体**；熔炼配方、锭类物品、
交互面板属玩法侧，见文末"下一步"。

## 为什么走 Blender 而不是 5080

`asset-model-workflow` 的形态分流（SKILL.md 第 22-26 行）把**规则构件、机械接头、薄壁与准确孔槽**
划给 Blender／Vibe3D 精确建模，5080 图生只用于冰锥、矿石、树干这类不规则粗糙主体；且地牢那 11 类
5080 候选已被用户整批否决。高炉是尺寸受 20 cm 建造格约束的规则砌体＋铸铁件，因此按分流走本地
Blender 程序化建模，不跑生成器、不抽种子。

## 设计契约（由宿主决定，不由审美决定）

| 项 | 值 | 依据 |
| --- | --- | --- |
| 占格 | 6 × 5 × 11 格 = **120 × 100 × 220 cm** | `FVoxelBuildPrefab::Footprint`，1 格 = 20 cm |
| pivot | 包围盒在 X／Y 居中、底面在局部 z = 0，`PivotOffsetCm = (0,0,0)` | `AVoxelBuildPrefabActor::ComputeTransform`：把网格**包围盒中心**对齐到占格盒中心，所以尺寸正好等于格数×20 时偏移为 0 |
| 朝向 | 出铁口／前床在 UE **+X（Actor 前方）**，风口鼓风管在 **+Y**，除灰门在 **-X** | Blender→UE 为 `(x, -y, z)`（先例 `DungeonWorkbenchKit20260921/Scripts/author_kit.py` 的 `ue()`） |
| 单位 | 厘米，Z 向上 | 与体素建造、构件调色板一致 |
| 尺寸自检 | 实测 `120.0 / 100.0 / 220.0`，误差 **0.0 cm**，中心误差 **0.0 cm** | `Authored/manifest.json` |

朝向在游戏里可随构件 90° 旋转变化（`RotatedFootprint` 会交换 X／Y 占格），所以朝向契约只定义
"0° 时哪一面朝前"。

## 分件

单一静态网格，内部由这些封闭实体组成（`Authored/manifest.json` 的 `parts` 有逐件包围盒）：

- **炉基**：凿角碎石垫层 → 线脚基座 → 琢石台身 → 斜面压顶。
- **炉身**：一根闭合旋转体，14 层砌块，每层带真实收分台阶（凸出 3.5 mm 的挑檐）与每层 ±2 mm 的
  偶然半径抖动，避免读成车床车出来的正圆锥。低处最粗（bosh，R 35.6 cm），向炉喉收到 R 23.8 cm。
- **炉顶**：挑出的牛腿环 → 直段炉冠 → 外翻炉唇 → 圆角炉口，内腔是**真实下沉的装料碗**（碗底
  27 cm 深），不是贴图假洞。
- **铁箍**：3 道环箍 + 每条 4 组六角螺栓带方形垫圈；4 条竖向拉条贴炉壁从底座贯到炉冠；炉冠另加 1 道箍。
- **风口与鼓风管**（+Y）：黏土炉衬圈 → 铸铁风口板（4 螺栓）→ 锥形风嘴 → Ø10 cm 鼓风管折弯下行 →
  带 6 螺栓的联轴法兰。法兰面是 `NS_ForgeSparks`／风箱的挂点。
- **出铁口与前床**（+X）：黏土出铁口护台，**布尔切出真实拱形孔洞**；冻结的渣舌；带渣底衬的斜溜槽；
  2 座砖支墩；浇铸床上 3 只**开口锭模**（也是布尔挖出的模腔，四面带搬耳）。
- **炉渣口**（+X 高位）：第二处布尔拱口 + 渣瘤。
- **除灰门**（-X）：布尔拱形凹口 + 铸铁门框、门扇、2 个铰链筒、闩。
- **炉前杂项**：浇铸床夯土面、6 块待装炉矿石、一处冻结渣摊。

## 材质分区（7 槽，均有完整 PBR）

| 槽 | 用途 | PBR 图 |
| --- | --- | --- |
| `BlastFurnace_Masonry` | 炉基垫层、基座、台身、压顶 | 2048，BaseColor/Normal/Roughness/Metallic/AO |
| `BlastFurnace_Firebrick` | 炉身砌块、牛腿、炉冠、炉唇 | 2048，同上 |
| `BlastFurnace_WroughtIron` | 铁箍、螺栓、风口、鼓风管、除灰门、锭模 | 1024，同上 |
| `BlastFurnace_ClayLuting` | 出铁口护台、炉渣口、风口衬圈、溜槽壁、夯土浇铸床 | 1024，同上 |
| `BlastFurnace_SlagLining` | 拱口内壁、溜槽底、锭模腔、渣瘤 | 1024，同上 |
| `BlastFurnace_EmberBed` | 装料碗底的余烬床（**发光材质替换点**） | 1024，同上 |
| `BlastFurnace_OreLump` | 待装炉矿石 | 1024，同上 |

贴图全部由 `prepare_furnace_textures.py` 用周期性 value noise 程序化生成，**完全可平铺**（缝在
贴图外），没有任何第三方素材。矿石/金属的晶面反光是独立 Metallic 通道，不是只画了颜色。

`EmberBed` 是留给运行时换发光材质的接口：炉子点燃时把槽 5 换成带 Emissive 的材质实例即可，不必改网格。

## 接口点（`manifest.json` 同时给 Blender 米制与 UE 厘米）

| 名字 | UE 坐标 (cm) | 用途 |
| --- | --- | --- |
| `ChargingMouth` | (-18, 0, 220) | 装料口中心，烟雾／火焰挂点 |
| `EmberBed` | (-18, 0, 186) | 碗底中心，火光／点光源挂点 |
| `BlastFlange` | (-18, -37.5, 62) | 鼓风法兰面，`NS_ForgeSparks`／风箱 |
| `TapHole` | (17.5, 0, 63.5) | 出铁口，铁水／火花流挂点 |
| `SlagNotch` | (15.5, 0, 95.5) | 排渣口 |
| `AshCleanOut` | (-53.2, 0, 70) | 除灰门，交互点候选 |
| `ForehearthFloor` / `CastingBedCentre` | (37.5, 0, 20) / (36.5, 0, 20) | 浇铸床面，锭产出摆放面 |

## 自检结果（制作自检，不是验收）

`author_blast_furnace.py` 结尾会断言并把结果写进 `Authored/manifest.json`：

- 尺寸误差 0.0 cm、XY 中心误差 0.0 cm、底面 z = 0 —— 满足占格契约。
- 边界边 **0**、非流形边 **0**、孤立点 **0**、退化面 **0** —— 全部封闭实体。
- 硬边顶点 2883 个（> 25° 判据），最大同点 loop 法线夹角 132.8° —— 硬边没有在导出时被抹平。
- 7 个材质槽、`UVMap` 一层（炉身柱面展开、其余按主法线平面投影，**每个多边形用它自己材质的平铺尺寸**）。
- 三角面 26204、顶点 13238。把导出的 FBX **重新导回 Blender** 读回：面数、点数、7 材质、1 层 UV
  与源网格逐项一致。

复跑自检：

```powershell
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background `
  'D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/Authored/BlastFurnace.blend' `
  --python 'D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/diagnose_topology.py'
```

## 修订 3（2026-09-23，改用库内写实素材）

用户反馈程序化贴图"不太写实、偏 lowpoly"，要求改用库里现成的写实材质。库普查结果与替换：

**来源**：`/Game/UnrealNormandy` —— Fab 的 **Sharur's Normandy Village + PCG Plants**
（`fab.com/listings/bf734560-f98b-4e4d-9a6c-e473b910a780`），工程已在体素块、丘陵地表、地牢残骸、
工具材质里广泛使用。既有做法是**新建自己的材质引用它、不改源资产**（`Docs/ProductionToolMaterials-20260913.md`），
本次沿用。

**RHAOM 打包语义从数据读出**（不是照名字猜）：**R = 粗糙度、G = 高度、B = 环境光遮蔽、A = 金属度**。
判据：R 通道呈现灰缝更粗糙的分布；B 通道正好把图集的干净砖区照成白色、涂抹区照成黑色。

| 槽 | 库内来源 | 说明 |
| --- | --- | --- |
| `Firebrick`（炉身） | `T_HB_Wall4x4_00A` 的干净砖区 | **库内没有可平铺的砖贴图**：该图集是废墟墙的实拍扫描图集，一半是拉伸涂抹；干净砖区裁出后**绕炉身只映射一圈**，u 接缝落在 315° 的竖向拉条下，因此不产生平铺接缝 |
| `Masonry`（炉基/垫层） | `T_StoneSurface_01A`（4096，带 Height） | 写实风化琢石，可平铺 |
| `WroughtIron`（铁箍/风口/锭模） | `T_MetalRust_00A`（4096） | 强橙锈；按工具材质的既有做法降饱和 0.62、压暗 0.72；金属度由粗糙度反推（导出丢了 alpha 通道） |
| `ClayLuting`（炉衬/夯土床） | `T_SoilSurface_02A` | 深棕土层 |
| `SlagLining`（拱口/挂渣） | `T_LC_BasaltCliff_00A` ×0.72 | 深色玄武岩 |
| `EmberBed`（余烬床） | `T_LC_BasaltCliffCracked_00A` ×0.55 | 龟裂深岩 |
| `OreLump`（矿石） | `T_LC_RockBasaltLichen_00A` | 带地衣的深色岩 |

**转成现有通道布局**：`build_library_textures.py` 把库图转成既有的
`BlastFurnace_<槽>_{BaseColor,Normal,Roughness,Metallic,AO}.png`，所以 **Blender 预览与 UE 材质图一行都不用改**，
只是贴图内容换了。转换脚本与本步回执：`build_library_textures.py`、`Authored/library-textures.json`。

**这一步连踩三个坑，都记在案**：
1. `Image.resize` / `thumbnail` 在这个 PIL 12.3.0 上对**文件来源的 4096 图返回全零**（合成图正常，
   `tobytes()` 数据也对）。改成 numpy 的 2×2 块平均降采样，对整数倍缩小本来也是更好的滤波。
2. `with Image.open(...)` 块里 `return np.asarray(image)` 返回的是**解码缓冲的别名视图**，块退出后内存释放，
   实测读出全零。必须 `np.array()` 复制。
3. 手工估的砖裁切上边界切进了图集涂抹区，渲染出**一圈青绿色带**。改成从 AO 通道校验裁切（涂抹区不烘焙
   AO，读数接近 0），不达标直接抛错。

## 修订 2（2026-09-23，按用户三条要求）

1. **砖块棱角圆润**。参考项目对体素块的既定做法（调色板 `EdgeRadiusCm = 1.4`，即 20 cm 块的 7%）
   与 Blender 侧先例（`PKMLowpoly20260922/build_mechanics.py:39`：角度限 35° 的 BEVEL + 3 段 +
   clamp overlap），给每类构件按尺度加 1.5–8 mm 圆角；炉身段数由 32 提到 **48**，并对炉身/铁箍开
   平滑着色——于是只有夹角超过 35° 的棱（课程挑檐、牛腿、炉唇）留硬边，柱面棱自然过渡。
   课程挑檐同时由 3.5 mm 加到 5 mm，给圆角留出咬入空间。三角面 6420 → **26204**，增加的全是真实圆角几何。
2. **金属重做**。见下节"反照率单位事故"——旧铁的线性反照率只有 **0.027**，等于黑铁。现在裸铁
   0.40 线性、锻鳞 0.135、锈 0.185 且为电介质，粗糙度从 0.30 提到 0.46（锈处 0.98），并加了
   抛光高点，让铁箍与螺栓在斜射光下有金属高光而不是一片死黑。
3. **流出物剔除**。用户圈定的是**斜溜槽本体**（`Tap_Gutter` + 2 座支墩），不是冻结渣块；上一轮把溜槽
   当"结构"留下是理解错误。该件已删，出铁口拱现在直接开在**空的浇铸床**上方，前面是 3 只**空锭模**。
   仍在模型里的：出铁口拱（炉壁上的开口，属结构）、浇铸床面、锭模本体。**没有任何"从炉里流出来的
   物质"**，等运行时的熔融材质/VFX 资产接进来。

## 反照率单位事故（这次最值得记的一条）

贴图 PNG 以 sRGB 编码保存、UE 里也按 sRGB 采样，所以**写进脚本的数值必须是线性反照率**。
第一版直接把 sRGB 数值当线性写（石材 `4F4E49`、铁 `2E2C2B`），解出来线性只有 **0.078 / 0.027**：
铁比黑体亮不了多少，怎么打光都没有金属感；石材也一直偏暗，害我两次误调曝光去"补偿"。

现在脚本用 `albedo(r, g, b)` **显式给线性值**，只在存盘时做一次线性→sRGB 编码，并把每种材质的
线性均值写进 `texture-recipes.json` 当证据：

| 材质 | 线性反照率（均值） | 参考 |
| --- | --- | --- |
| Masonry | 0.220 / 0.217 / 0.206 | 琢石石灰岩 |
| Firebrick | 0.196 / 0.145 / 0.105 | 耐火砖 |
| WroughtIron | 0.310 / 0.270 / 0.248 | 裸铁 0.40 + 锻鳞 + 锈的混合 |
| ClayLuting | 0.130 / 0.083 / 0.053 | 夯土／黏土炉衬 |
| SlagLining | 0.071 / 0.069 / 0.067 | 挂渣釉面 |
| EmberBed | 0.069 / 0.039 / 0.032 | 余烬床 |
| OreLump | 0.068 / 0.058 / 0.048 | 矿石 |

## UE 侧独立进程读回

`verify_blast_furnace.py` 在**另一次 commandlet**里读回（不是写它的那个进程），回执
`verify_receipt.json`：

- 网格 `120.0 × 100.0 × 220.0 cm`，包围盒原点 `(0, 0, 110)`（底面在 z = 0，与占格契约一致）。
- 7 个槽全部绑到 `/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_*`。
- Nanite 开；`collision_trace_flag = CTF_USE_COMPLEX_AS_SIMPLE`。
- 调色板 22 条：原有 21 条（罗马柱、栏杆、门、窗、广场喷泉、祭坛……）**逐条保留**，只追加
  `blast_furnace` `[6, 5, 11]`、`pivot_offset_cm = (0,0,0)`。
- 7 个材质各 16 个表达式，`BaseColor / Roughness / Metallic / Normal` 四个输出**都**接到了真实节点
  （`recompile_material` 返回 `[]` 只能证明能编译，证明不了接对）。

### 一个读数陷阱：Nanite 网格的 `get_num_triangles(0)`

UE 读回 `get_num_triangles(0) = 4764`，比源网格 6420 少 1656。**这不是几何丢失**，证据链：

1. 把 FBX 导回 Blender：6420 面 / 3358 点，与源一致 → 文件没缺东西。
2. 在包内做退化面普查：面积 < 1e-6 m² 的三角形 **0 个**；按 0.01 cm 焊接，面数 **一个不掉**。
3. **对照组**：对已发布、README 记录为 139062 三角面的方形祭坛调同一个 API，返回 **2164 面**、
   3619 顶点。同一个调用在已知资产上差了 64 倍。

所以在本版引擎里，Nanite 网格的 `get_num_triangles(0)` 返回的不是作者面数（`fallback_percent_triangles`
读回是 1.0，也没解释这个差值）。**不要用这个读数为"导入掉面"作证**，也不要用它当制作面数记账；
要核对面数就把 FBX 导回 Blender 数。`probe_triangle_count.py` 是这次对照用的探针，保留备用。

## 制作过程中真正修掉的三个 bug

记在这里是为了别的构件不要重踩：

1. **蝴蝶结四边形**。`box()`／`frustum_box()` 原先把角点写成 `(-,-),(+,-),(-,+),(+,+)`，第 1→2 条边走
   的是对角线：每个侧面四边形都是 bowtie，三角化后两面法线正好 180°，基座、浇铸床、锭模、支墩全是
   坏几何。判据就是自检里的"同点 loop 法线最大夹角 = 180°"。正确顺序是 `(-,-),(+,-),(+,+),(-,+)`。
2. **闭合环旋转体的缝**。矩形截面铁箍的剖面首尾点重合，但代码给首尾各建了一环顶点：几何闭合、
   拓扑开放，288 条边界边。闭合环必须复用首环（`(i+1) % count`）。
3. **UV 平铺尺寸取错槽**。每个部件都挂满 7 个槽（布尔 `material_mode='TRANSFER'` 需要按索引映射），
   于是"取 `data.materials[0]` 的平铺尺寸"永远取到槽 0 的砌石 2.25 m —— 耐火砖被拉成米级大白块。
   UV 必须**逐多边形**读它自己材质的平铺尺寸。
4. **反照率单位写错**（见上节）：把 sRGB 数值当线性反照率写，铁只有 0.027 线性。判据是"金属怎么打光
   都不亮"，而不是"灯不够"。

## 使用入口

- 静态网格：`/Game/Props/BlastFurnace20260923/SM_BlastFurnace`
- 材质：`/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_*`
- 贴图：`/Game/Props/BlastFurnace20260923/Textures/T_BlastFurnace_*`
- 建造面板条目：稳定 ID `blast_furnace`，显示名"冶炼高炉"，登记在活动调色板
  `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`（只追加，保留其他条目与字段）。
- **面板归属（2026-09-23 用户指定）**：调色板条目的 `Material` 字段**留空**，所以列在建筑面板的
  **「其他」标签页**，不在「材质 → 石头 → 其他构造」里。`VoxelBuildWidget.cpp:744` 的规则是
  "「其他」只列未归类构件"，清空该字段即是归类到「其他」；改动用 `set_furnace_drawer.py` 落盘，
  回执 `drawer_receipt.json` + 独立进程读回 `drawer-verify.json`。
- 碰撞走 `CTF_USE_COMPLEX_AS_SIMPLE`（三角面即碰撞体），因为装料碗是凹的，包成凸体会把炉口填死；
  网格启用 Nanite。

## 可编辑源与重制

```
SourceAssets/BlastFurnace20260923/
  prepare_furnace_textures.py     # 系统 python + numpy/PIL：程序化 PBR（修订 3 起备用，被库贴图取代）
  build_library_textures.py       # 系统 python：把 UnrealNormandy 库图转成既有通道布局（当前正式来源）
  probe_normandy_library.py       # UE commandlet：普查库内材质球/贴图（只读）
  probe_normandy_library2.py      # UE commandlet：材质实例参数与贴图尺寸（只读）
  export_normandy_textures.py     # UE commandlet：把库贴图导出成 PNG（TextureExporterPNG）
  prepare_normandy_preview.py     # 系统 python：降采样 + 候选基色对照表
  author_blast_furnace.py         # Blender 无头：几何 + 圆角 + 材质 + UV + FBX + blend + manifest
  render_furnace_verification.py  # Blender 无头：6 视角 × 白膜/贴图 两趟
  preview_blast_furnace.py        # Blender 无头：单趟贴图预览（更轻，输出 Authored/Preview/）
  render_furnace_elevation.py     # Blender 无头：正交立面（透明胶片）＋ 180 cm 人形参照
  annotate_elevations.py          # 系统 python：按 alpha 实测轮廓并标注尺寸
  diagnose_topology.py            # 只读：开放边／退化面／法线夹角定位
  install_blast_furnace.py        # UE commandlet：首次安装（分阶段、已存在则保留）
  revise_blast_furnace.py         # UE commandlet：显式修订（删除后全新导入网格）
  set_furnace_drawer.py           # UE commandlet：把条目挪进「其他」标签页（清空 Material 字段）
  verify_furnace_drawer.py        # UE commandlet：独立进程确认面板归属
  verify_blast_furnace.py         # UE commandlet：独立进程读回网格/材质/调色板
  probe_triangle_count.py         # UE commandlet：Nanite 面数读数对照探针
  Authored/BlastFurnace.blend     # 可编辑源（贴图已打包）
  Authored/SM_BlastFurnace.fbx    # UE 导出网格
  Authored/Textures/*.png         # 35 张 PBR 图（源自库贴图转换，本机文件不入库）
  Authored/library-textures.json  # 库贴图来源、RHAOM 通道语义、逐槽线性反照率
  Authored/manifest.json          # 制作回执：尺寸、拓扑、材质槽、接口点、逐件包围盒
  Authored/Verify/*.png           # 白膜/贴图两趟 + 标注立面（本机文件，不入库）
  install_receipt.json / revise_receipt.json / verify_receipt.json
```

重跑顺序（前两步幂等，第三步对已存在资产会保留不覆盖）：

```powershell
# 1) 库贴图 -> 既有通道布局（当前正式贴图来源；程序化脚本为备用）
python SourceAssets/BlastFurnace20260923/build_library_textures.py
# 2) Blender 建模 + 导出
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup `
  --python SourceAssets/BlastFurnace20260923/author_blast_furnace.py
# 3) UE 接入：首次用 install（已存在则保留），修订用 revise（删除后全新导入网格）
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript `
  '-script=D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/revise_blast_furnace.py' `
  -unattended -nop4 -nosplash `
  '-abslog=D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/revise.log'
# 4) 独立进程读回（不要用写它的那个进程验证自己）
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript `
  '-script=D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/verify_blast_furnace.py' `
  -unattended -nop4 -nosplash `
  '-abslog=D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/readback.log'
```

二进制（`.blend`／`.fbx`／`.png`）按仓库既定忽略规则只保留在本机。

## 交付状态

- **已生成**：几何、7 套 PBR 图（源自 UnrealNormandy 库贴图转换）、`.blend`、`.fbx`、manifest、库贴图来源回执。
- **已导入**：见 `install_receipt.json` 与 `Saved/BlastFurnace20260923/install.log`。
- **未编译**：本次没有任何 C++ 改动。
- **未测试**：没有启动 PIE、没有截图、没有渲染验收。上面的 6 张自检图是制作期排查用的，
  不等于用户的视觉验收。
- 观感、比例与手感由用户实机判断。

## 下一步（本次范围外）

1. **熔炼玩法**：`crafting-recipes.json` 式的矿石→锭配方；`items.json` 目前只有 `ironOre / copperOre /
   silverOre / goldOre`，**没有锭类物品**，需按 `ue5-item-asset-workflow` 补定义与图标。
2. **交互与表现**：`E` 交互打开熔炼面板；把 `NS_CauldronBlacksmith`／`NS_ForgeSparks` 挂到
   `ChargingMouth`／`BlastFlange`／`TapHole`；碗底槽换成发光材质实例。
3. **放置口径**：O2 要求四个设施都能被玩家放进自造建筑并与建造系统共用放置／扣料／回收。构件目前
   免料（Backlog 第 16 条），要先给高炉定义物品再走同一套扣料。
4. 若实机觉得炉身砌块层次不够，可提高 `COURSE_COUNT` 或把炉身段数从 32 提到 48 重跑；
   **不要**靠提高贴图分辨率来换几何层次。
