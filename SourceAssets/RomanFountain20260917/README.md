# 罗马喷泉（蛋糕塔）2026-09-17

按 `skills/ue5-pcg-building` → `skills/asset-model-workflow` → `Docs/Building/voxel-build-workflow.md`
的链条制作的第三件大理石家族建筑构件（前两件：罗马凉亭、栏杆套件）。

## 成品

- **`/Game/Props/RomanFountain20260917/SM_RomanFountain_20`** — 单件整体喷泉，11 个独立壳体
  （8 个大理石旋成体 + 3 个碗腔水体），**全程零 self_union**（bTrimFlaps 塌曲率坑）。
  资产 21,696 tri（动态网格 25,920 中 4,224 个贴轴零面积三角被资产导入阶段自动剔除，
  25920−4224=21696 精确对账）。**2026-09-18 起 SCALE=2**：几何整体放大一倍 → 包围盒
  **960×960×720** 逐轴精确 20 的倍数 → 占格 **48×48×36**，pivot 底面中心（origin z=360），
  XAtlas UV；缩放走原生 GeometryScript（copy→scale→copy back，拓扑不变故 tri 数不变），
  碰撞从存储盒改为 **complex-as-simple 三角碰撞**（随缩放自动生效）。1× 造型可把
  `build_fountain_20260917.py` 的 `SCALE` 改回 1.0 重建。
- **水体 v2（用户否决了 v1 悬空水盘）**：v1 是 4 cm 厚薄圆片悬在碗腔里，盘底与碗底之间隔着
  10–12 cm 空气，透射看像浮在半空。v2 把水体做成**碗腔剖面从碗底到水面线的旋成填充体**：
  侧边界向大理石壁内推 1 cm（所有侧面埋进不透明实体——既无空隙也无共面 z-fighting），
  底面低于碗底 1.5 cm 埋进盘底实体，只露顶面，水面与碗壁相交处是干净的水线。
  水面高度不变（58 / 200 / 280），柱墩与松果顶饰照常穿出水面。
- 材质双槽：slot0 `M_RomanStone_V2`（大理石家族统一材质）、slot1 项目自带
  `/Game/WaterMaterials/Materials/M_Water_Clean`（水体独立走 `material_id=1` 壳体分组，
  `set_asset_materials("marble,water")` 按槽序赋值——无需新建水材质）。
- 碰撞：`generate_collision(AlignedBoxes)` → **8 盒体、0 convex/sphere/sphyl/taper**
  （每个连通壳体一个盒；生成器没有给旋成体塞胶囊，读回确认过）。

## 造型（自下而上，单位 cm）

两级 10 cm 台阶（240/220）→ 大水盘 r206（碗底 44，盘沿 82）→ 车削柱墩 r84 穿水而上 →
中水盘 r134（碗底 184，沿 214）→ 柱墩 r62 → 顶水盘 r91（碗底 266，沿 286）→
松果顶饰（pigna，梵蒂冈松果喷泉剪影，z 262..360）。每件向下咬合 4 cm 防共面 z-fighting；
水盘半径均按水面高度处碗壁内径收过（盘缘小于该高度壁径 ≥6 cm，不穿壁）。

## 接入

- 调色板：活动 `Rounded/DA_VoxelBuildPalette` 新增第 13 条 `roman_fountain` /
  「罗马喷泉（蛋糕塔）」/ 24×24×18 / Surface=M_RomanStone_V2 / `Material="marble"`（大理石行
  「其他构造」）/ 普通构件（ActorClass 空）。其余 12 条 9 字段原样保留，门构件 actor_class 完好。
- 地图：DayNight_Lighting 新增 `RomanFountain1`（StaticMeshActor，1350,−1150，网格底 z=0），
  凉亭正南 750、避开 y=600 地砖排与 y=930 围栏；摆位由脚本按"地面覆盖 + 480×480×360 包围盒
  不与任何 StaticMeshActor 相交"自动选点。`save_current_level` 落盘 FRESH。
- 面板缩略图由运行时图标子系统渲染（正交 78%、−18/−35），无静态图可塞，见工作流 §5.2。

## 验证（全部完成，除实机体验外）

| 项 | 结果 |
| --- | --- |
| 几何（11 壳、0 开放边、bbox 逐轴 480/480/360） | OK |
| 磁盘落盘（mesh 661 KB / palette / umap 三件 mtime FRESH） | OK |
| 离线 OBJ 法证：0 NaN、0 边界边、11 壳环绕一致（负号=UE 顺时针正面） | OK |
| 碰撞形状读回 8 盒体零杂散 | OK |
| 材质槽读回 marble+water | OK |
| **第二进程**独立读回（资产/调色板/关卡 30 项，含 2× 与水柱复检） | **30/30 PASS** |
| 用户实机（进游戏看喷泉、面板卡片、水材质观感） | **待用户** |

## 作者脚本

- `build_fountain_20260917.py` — 无头构建（资产+调色板先写，load_map/摆场最后，同进程顺序硬规则）。
- `verify_fountain_20260917.py` — 第二进程读回验证 26 项。
- `probe_20260917.py` / `probe2_20260917.py` — 前置探测（API 签名/水材质清单/槽位语义）。
- `forensic_fountain.obj` — 动态网格全量 dump（离线法证输入）。

## 本次新踩的坑（已沉淀进记忆/工作流）

1. **漏调 `generate_collision` 不报错**：`save_mesh_to_static_mesh(enable_collision=True)` 只建
   空 BodySetup（形状全 0），必须显式 `SV.generate_collision(...)` 后再读形状计数。
2. **`StaticMaterial` 结构体在 5.8 Python 里既没有 `material_asset` 也没有 `material` 的
   editor property**——读槽位材质用 `StaticMesh.get_material(i)` 方法。
3. **数场景 actor 用 `get_actor_label()`**：之前会话用 `set_actor_label` 打的
   `RomanPavilion2_*`/`RomanFence_*`，内部 `get_name()` 仍是 `StaticMeshActor_N`，
   按内部名前缀统计会得 0（差点误判凉亭/围栏丢失）。
4. 旋成剖面贴轴（r=0 起止）产生的零面积三角形由资产导入自动剔除，属正常产物；
   UE 环绕约定下离线右手定则体积为负 = 正确外向。


## 2026-09-18 二次迭代：放大一倍 + Fab 水流特效

- **放大一倍**：用户指定整体拉伸 ×2。因当次编辑器会话没有 ModelingService 绑定
  （Vibe3D 注册缺失），改用 UE 原生 GeometryScript 路线完成资产级缩放；脚本
  `scale_fountain_2x_20260918.py`（带防重入护栏：已 2× 则跳过几何缩放，防连跑变 4×）。
  调色板占格同步 48×48×36，场景 RomanFountain1 重新贴地 z=-360。
- **水柱特效**：引擎 Niagara 模板 `/Niagara/DefaultAssets/Templates/Systems/FountainLightweight`
  以 NiagaraActor（`RomanFountainFX_Jet`，scale 1.2）挂在 pigna 尖端 (1350,-1150,720)，
  **attach 到 RomanFountain1**（移动喷泉水柱跟随）。脚本 `add_fountain_fx_20260918.py`。
  注意：面板调色板摆出的喷泉不带此特效（它是关卡 actor，不是构件的一部分）。
- **音效缺口（如实记录）**：全项目声音资产（192 SoundWave + 29 SoundCue，注册表全量盘点）
  **没有水流/瀑布环境声**；本地 Fab 工程 FabNatureExport 也只有植物地形。唯一水相关是
  FreeFootsteps 的一次性脚步水花（S_splash1/2 + deep），循环播放不能当水流声。
  要配水声需从 Fab 商店取一个 water loop 包再接 AmbientSound；或写代码用脚步水花做
  近距离落水随机音（未做，等用户定）。
- **新坑**：无头 commandlet 里 `LevelEditorSubsystem.is_in_play_in_editor()` 会
  **ACCESS_VIOLATION 崩进程**（无头没有关卡编辑器状态）——PIE 查询只能在运行中的编辑器里做；
  无头脚本用 `FOUNTAIN_HEADLESS=1` 环境变量跳过（脚本内已内置该护栏）。
- 验证：第二进程 30 项读回全 PASS（含 2× bbox/占格/贴地、水柱存在/资产/父子/位置）。


## 2026-09-18 三次迭代：水体 v3（材质 + 水位 + 挪位）

用户反馈 2× 后水体"仍有悬空感"。几何本身是贴壁的（v2 已埋边），观感问题有三个来源，全部处理：

1. **材质**：`M_Water_Clean` 低透明度，透过水面直接看见碗底——正是"玻璃片浮在碗里"的观感。
   换成项目自带 **`M_Water_Opaque`**（`/Game/WaterMaterials/Materials/M_Water_Opaque`），
   完全不透，读作实心水体。脚本内 `pick_water_material()` 带回退。
2. **水位**：三处水面抬高到近沿（74 / 206 / 282，沿下 8 / 8 / 4 cm），水和盘沿、柱墩连成一体，
   不再有深色碗壁带隔在水面与沿之间。剖面边界仍严格按碗壁内径 +1 cm 埋边。
3. **挪位（放大遗留问题）**：2× 后喷泉在原位 (1350,-1150) 的包围盒与凉亭台基重叠 210 cm
   （1× 时贴边 30 cm 是按 480 足尺寸算的）。移到凉亭正南轴线 **(1350,-1550)**，
   南缘距台基 190 cm；水柱曾被拖到塔身内（z=370），已复位塔尖 (z=720) 并重新挂接。
   挪位脚本 `place_fountain_2x_20260918.py`，选址依据 `scan_level_20260918.py`
   （Floor 为 500m 大地板；BP_FPS_DayNightManager 的边界箱是逻辑边界、非物理，clash 探测要忽略）。

顺带：调色板现 16 条（并行任务加了 window_wood/stone/marble 三条窗户构件），喷泉条目完好。
验证：第二进程 30 项读回全 PASS（含新坐标、水柱位置、材质变体）。


## 2026-09-18 四次迭代：真正的悬空根因 = 中央支撑比例（socle 基座）

用户第三次反馈"更明显了"并附实拍截图。定位结论修正：v2/v3 的水几何与材质都对
（Opaque 不透、水贴壁满填），截图暴露的是**结构问题**——直径 8.2m 的水盘上，中层塔身
悬挑在水面之上，中央支撑只有 2.4m 粗且恰在背光阴影里（阴影里的水渲染成黑色弯月），
读作"塔浮在水面上"。

**修复**：给塔加从水里长出来的基座（GeometryScript 原生路线，无需 ModelingService）：
- 底环 r208（z 84..112，咬进盘底 4cm）
- 锥形鼓座 r196→r156（z 112..248），水面 z=148 处鼓座 r≈182 → 塔身与水面相交处有清晰的
  水线圆，中层悬挑被大质量石座承托
- 新壳体与水体共面相交无 z-fighting（锥面穿过水面为横截线）；水盘内的水面被不透明鼓座遮住
- 资产 +1,536 tri（总 23,808），bbox/占格/材质槽不变，落盘 631,932 B；碰撞无需改
  （基座整体在既有盒体体积内）。脚本 `add_socle_20260918.py`。

**水材质盘点（用户问"游戏中有几种"）**：注册表全量 147 个水相关材质，其中引擎插件自带
约 100 个（Water 插件 60、流体模拟 33、Landmass 18 等）；**Fab 导入的游戏资产包
`/Game/WaterMaterials` 26 个**（Ocean/Lake/Rapids/Waterfall/PondScum/Clean/Opaque 等全家桶），
另有河流 8、雨洼 2、溅水 3、VFX 水滴 4 等零散包。喷泉引入过 2 个：M_Water_Clean（半透明，
v1-v2）→ M_Water_Opaque（不透明，v3；**无暴露参数，不能调色**）。

**未竟事项**：实拍自检失败——用户编辑器反复开关 + PIE 占用，远程通道抢不到稳定窗口；
无 RHI commandlet 里 SceneCapture 渲染链崩溃（exit 2，死在 capture 设置段）。下次编辑器
稳定非 PIE 时跑 `shot_socle_20260918.py` 可出两张验证图。

**注意**：用户的编辑器会话可能还持有旧版网格（内存中），需要重启 PIE/编辑器才会看到基座。


## 2026-09-18 五次迭代：更像水 + 溢流落水 + 逻辑构件（水体 v5）

用户口径："更像水 + 做溢流和落水（从上往下流淌），水声用占位，可以接受为逻辑构件。"
完整记录见 [Docs/Building/fountain-water-20260918.md](../../Docs/Building/fountain-water-20260918.md)。本轮要点：

- **找到一处真·悬空**：关卡的 `RomanFountainFX_Jet` 是硬编码 z=720，而喷泉 actor 在 z=−360、网格高 720
  → 水柱比塔尖高 360 cm。新逻辑构件 `AColdSteelFountain` 的水柱位置**按主网格包围盒算**，关卡实例已迁移（旧的两个 actor 合成一个）。
- **水面换回半透明**：`SM_RomanFountain_20` slot1 = `MIC_FountainWater`（父 `M_Water_Clean`，带深度淡出/多层波浪/暴露参数），
  v3 的 `M_Water_Opaque` 平板读法作废；盆底加焦散衬底。
- **接触与运动**：新增 `SM_RomanFountain_WaterFX`（20 件薄壁实体、13,184 tri、4 槽）：三级水线泡沫环 + 湿痕带 +
  穿出物接触环 + **三级溢流水帘（含台阶短帘）** + 落点泡沫环 + 盆底焦散。水膜材质 `M_FountainWaterFilm` **自算柱面 UV**，
  泡沫按世界尺寸滚动，不依赖 XAtlas UV。
- **接入**：调色板 `roman_fountain` 的 ActorClass → `ColdSteelFountain`（面板摆出来也有水效，占格 48×48×36 不变）；
  质量开关 `fps.Fountain.Quality`；水声按用户要求先用脚步水花**占位**。
- 未做：水柱仍是引擎模板（没有落回/水雾粒子）、无粒子层、无正式水流声、性能未实测。


## 2026-09-18 六次迭代：水体 v6（更像水 + 落水驱动 + 性能分级）

用户回执"还是很假、完全没有流动感、像个固体"（附 PIE 截图），并要求先调研 GitHub 水体项目、评估现有资产。
调研结论 + 实现见 [Docs/Building/fountain-water-20260918.md](../../Docs/Building/fountain-water-20260918.md) 第 6 节。要点：

- **不需要第三方**：引擎已装 Water/WaterAdvanced（浅水 SWE、`Water_Material_Simple`、焦散生成）与 NiagaraFluids（`BP_WaterRenderer`）；
  开源那几家（NiagaraFluid SPH、FluidForge、GVDB FLIP、undine）都是模拟实验/早期项目，不适合可反复放置的喷泉。
- **水面换成自制材质** `M_FountainWater`（58 表达式）：极坐标双层滚动法线 + **落点驱动的解析涟漪** + 场景深度配色 +
  菲涅尔天空反射 + 波峰白沫；`MIC_FountainWater` 全部参数（23 scalar / 2 vector / 3 texture）可调。
- **水帘提亮加速**（`MIC_FountainCascade`）、**新增 4 个落点水花**（引擎模板缩到 0.42）。
- **性能**：近/中/远距离分级（26 m / 62 m）、`fps.Fountain.Quality 0` 一键全关、水效网格排除出 RT 几何与距离场。
- B 档（浅水 SWE 真模拟）本轮**用解析涟漪替代**（理由与升级路径见文档 6.3）；水雾/飞沫、WPO 摆动、正式水声仍未做。
