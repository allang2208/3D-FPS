# 冶炼高炉世界模型（O2 野外设施）

2026-09-23。O2「野外设施模型」里**高炉本体**这一项完成并接入。作者源、逐件数据与完整制作记录在
[SourceAssets/BlastFurnace20260923/README.md](../../SourceAssets/BlastFurnace20260923/README.md)；
本文件只记项目口径的结论、入口与剩余工作。

## 分流依据

按 `asset-model-workflow` 第 22-26 行的形态与精度分流：高炉是**尺寸受 20 cm 建造格约束的规则砌体
加铸铁件**（准确拱形孔洞、法兰、螺栓、开口锭模），属于"精细／规则构件"，走本地 Blender 精确建模；
不跑 5080 生成器，也不把增加步数或贴图分辨率当成恢复结构的手段。地牢那 11 类 5080 候选的整批否决
不覆盖本条，本条也不据此宣布生成管线能力上限。

## 交付口径

- 静态网格 `/Game/Props/BlastFurnace20260923/SM_BlastFurnace`，7 个材质槽，均带完整 PBR 图
  （BaseColor／Normal／Roughness／Metallic／AO，程序化生成、可平铺、无第三方素材）。
- 建造面板：**其他 → 冶炼高炉**，稳定 ID `blast_furnace`；登记在活动调色板
  `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`，只追加不覆盖。归入「其他」的方式是
  **把条目的 `Material` 字段留空**（`VoxelBuildWidget.cpp:744`：其他标签只列未归类构件），
  2026-09-23 用户指定，改动回执 `drawer_receipt.json` + 独立进程读回 `drawer-verify.json`。
- 占格 **6 × 5 × 11 = 120 × 100 × 220 cm**，`pivot_offset_cm = (0,0,0)`（网格尺寸正好等于格数×20）。
- 碰撞 `CTF_USE_COMPLEX_AS_SIMPLE`（装料碗是凹的，凸体会填死炉口），启用 Nanite。
- 朝 UE +X 的一面是出铁口／前床；鼓风管在 +Y；除灰门在 -X。构件 90° 旋转会交换占格，朝向随旋转走。

## 已发布接口点（给玩法与特效接入用）

`ChargingMouth (-18,0,220)`、`EmberBed (-18,0,186)`、`BlastFlange (-18,-37.5,62)`、
`TapHole (17.5,0,63.5)`、`SlagNotch (15.5,0,95.5)`、`AshCleanOut (-53.2,0,70)`、
`ForehearthFloor (37.5,0,20)`、`CastingBedCentre (36.5,0,20)`，单位 cm，坐标见
`Authored/manifest.json`。`EmberBed` 槽是为运行时替换发光材质留的，点炉不必改网格。

## 状态边界

- **已完成**：建模、7 套 PBR、FBX／blend、导入落盘、调色板注册、**独立进程读回**（网格尺寸／7 槽绑定／
  Nanite／复杂碰撞／调色板 22 条保留原 21 条／7 个材质四个输出全部接通）。
- **修订 2（2026-09-23，按用户三条要求）**：① 砖块棱角按项目体素块的既定做法（调色板
  `EdgeRadiusCm = 1.4` ＝ 20 cm 块的 7%；Blender 侧先例 `PKMLowpoly20260922/build_mechanics.py:39`
  的角度限 35° BEVEL + clamp overlap）加工 1.5–8 mm 圆角，炉身段数 32 → 48 并开平滑着色，
  三角面 6 420 → **26 204**；② 金属重做——旧铁线性反照率只有 **0.027**（把 sRGB 数值当线性写），
  等于黑铁，现为裸铁 0.40 线性 + 锻鳞 + 锈（电介质），粗糙度 0.30 → 0.46；③ **剔除"流出来的
  物质"**——用户圈定的是**斜溜槽本体**（`Tap_Gutter` + 2 座支墩），已删；出铁口拱现在直接开在空的
  浇铸床上方，前面是 3 只空锭模。仍在模型里的只有结构：拱口、浇铸床面、锭模本体。
  贴图与网格走 `revise_blast_furnace.py` **原地替换**（保留调色板对网格的软引用），回执
  `revise_receipt.json`。
- **修订 3（2026-09-23，按用户"改用库内写实素材"）**：程序化贴图被判"不太写实、偏 lowpoly"，
  已整套换成工程自有的 **UnrealNormandy**（Fab「Sharur's Normandy Village + PCG Plants」）4096 实拍
  贴图。**库内没有可平铺的砖贴图**——`T_HB_Wall4x4_00A` 是废墟墙的实拍扫描图集，一半是拉伸涂抹；
  干净砖区裁出后**绕炉身只映射一圈**（u 接缝落在 315° 竖向拉条下）以避免平铺接缝。其余：砌石
  `T_StoneSurface_01A`、锈铁 `T_MetalRust_00A`、夯土 `T_SoilSurface_02A`、玄武岩 `T_LC_BasaltCliff_00A`、
  龟裂岩 `T_LC_BasaltCliffCracked_00A`、矿石 `T_LC_RockBasaltLichen_00A`。RHAOM 打包语义**从数据读出**：
  R=粗糙度、G=高度、B=AO、A=金属度。转换脚本 `build_library_textures.py` 输出既有通道布局，
  所以 Blender 预览与 UE 材质图都无需改动。沿既有做法：**新建自己的材质引用库贴图，不改源资产**。
- **已完成**：建模、7 套 PBR（库内写实素材）、FBX／blend、导入落盘、调色板注册、**独立进程读回**、
  **归入建筑面板「其他」标签页**（`Material` 字段清空，独立进程确认）。
- **已完成（同日玩法侧）**：冶炼面板与熔炼接入——E 交互开背包＋左侧冶炼面板、4 种锭物品
  （占位图标）、`smelting-recipes.json` 配方、炉内**燃料模型**冶炼（木材 20 秒/件、存料封顶
  300 秒；有燃料才按真实时间推进，建造存档 VBX v6，v5 挂钟档读入时自动迁移）、双列加粗进度条
  （左＝脉冲进度、右＝燃料火星）＋添加燃料按钮、拆除退料含燃料折木材。
  规划与实现记录见 [冶炼面板规划](../UI/smelting-panel-plan-20260923.md) 第 7／7.1 节。
- **未做**：Niagara 特效挂点、放置扣料口径、取代流出物的熔融材质/VFX 资产。
- **未测试**：没有启动 PIE、没有截图、没有渲染验收。制作期的白膜/贴图对照图（`Authored/Verify/`）
  与标注立面是排查用的，不是用户的视觉验收；比例、观感与手感由用户实机判断。

## 三条要记住的坑

1. **UE 里 `get_num_triangles(0)` 不能用来看导入有没有掉面**。本网格源是 6 420 面时该调用返回 4 764；
   把 FBX 导回 Blender 读回是 6 420 面 / 3 358 点，且面积 < 1e-6 m² 的退化三角形为 0、按 0.01 cm
   焊接一个面都不掉。用已发布、记录为 139 062 面的方形祭坛调同一个 API，返回 **2 164 面** ——
   同一个调用在已知资产上差 64 倍。核对面数请把 FBX 导回 Blender 数。
2. **BaseColor 贴图是按 sRGB 采样，脚本里必须写线性反照率**。第一版把 sRGB 数值当线性写，铁的线性
   反照率只有 0.027，怎么打光都没金属感——症状会被误读成"灯不够"而去调曝光。现在脚本用
   `albedo(r,g,b)` 显式给线性值，只在存盘时编码一次，并把每种材质的线性均值写进
   `Authored/texture-recipes.json` 当证据。
3. **修订网格不要用 `AssetImportTask.replace_existing=True`**。它走 UE 的重导路径，复用资产里已存的
   导入设置而不是本次的 `FbxImportUI`；同一个脚本第二次替换时单位缩放被叠加，留下一个 **1.2 cm**
   的网格（源 120 cm），而脚本自己读回的 `get_bounds()` 也一起缩放，"自报尺寸"照样通过 ——
   是**独立进程读回**才抓到的。现在改为 `delete_asset` 后全新导入，并在导入后**断言占格尺寸**
   （20 cm 格的构件尺寸是存档契约）。删掉再重建不影响调色板：软对象路径同路径解析，复核 22 条
   条目无一丢失 mesh 引用。

## 下一步

1. ~~`items.json` 补锭类物品与图标~~ **已做（2026-09-23）**：`ironIngot/copperIngot/silverIngot/goldIngot`
   ＋ PIL 占位图标；正式渲染图仍按 [非枪械物品工作流](../../skills/ue5-item-asset-workflow/SKILL.md) 补。
2. ~~矿→锭配方与熔炼面板~~ **已做（2026-09-23）**：`smelting-recipes.json` ＋ E 交互冶炼面板；
   投料用 `ConsumeItem`（背包优先、仓库兜底，背包＋仓库合计口径），未另建库存。
   输入定为材料线 `iron_ore/copper_ore/silver_ore/gold_ore`（矿镐采集线，不是祭品线 `ironOre`）。
3. `NS_CauldronBlacksmith` / `NS_ForgeSparks` 挂到上面三个口；碗底槽换发光材质实例。
4. 放置扣料：构件目前免料（Backlog 第 16 条），要先给高炉定义物品再接入同一套放置／扣料／回收。
