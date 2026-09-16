# 罗马柱建模（2026-09-15）

用户要求：在 UE 引擎内直接建模一根罗马柱，并包含石膏材质。

## 做法

全程在**运行中的编辑器内**用 Vibe3D 的会话网格算子完成（`unreal.ModelingService`），脚本经 Python 远程执行通道送入，一次连接跑完全部步骤——没有走 Blender，也没有每次调用一次 HTTP 往返。

| 项 | 值 |
| --- | --- |
| 作者脚本 | `build_roman_column.py` |
| 通道 | `Tools/AssetPipeline/ue_python_exec.py`（Python 远程执行，一次连接） |
| 单位 | 厘米 |
| 运行耗时 | 约 3.6 秒（含节点发现、连接、执行、回传） |

## 构件与尺寸

| 部位 | 构造 | 尺寸 |
| --- | --- | --- |
| 柱础底板 | box | 76 × 76 × 10 |
| 柱础圆盘 | cylinder | Ø64 × 6 |
| 柱础圆环 | torus | 主半径 30 / 管半径 4 |
| 凹弧过渡 | cone | Ø60 → Ø46 × 10 |
| 柱身 | cylinder，64 边 | Ø44 × 200（z 30–230） |
| 凹槽 | `cut_groove_along_polyline` × 20 | 槽宽 3.6、深 1.1 |
| 柱头颈环 | torus | 主半径 23 / 管半径 2.5 |
| 柱头钟形 | cone | Ø46 → Ø62 × 14 |
| 柱头顶板 | box | 64 × 64 × 9 |

总高 257 cm，包围盒 76 × 76 × 257 cm。

## 运行资产

| 资产 | 路径 |
| --- | --- |
| 静态网格 | `/Game/Props/RomanColumn20260915/SM_RomanColumn` |
| 石膏材质 | `/Game/Props/RomanColumn20260915/M_Plaster` |

石膏材质为 3 个参数节点的简单材质：`PlasterColor` 向量参数（0.86, 0.84, 0.80）、`PlasterRoughness` 标量参数 0.76、`PlasterMetallic` 标量参数 0。BaseColor / Roughness / Metallic 均已连线并编译。

## 核对结果（读回资产，非渲染验收）

- 网格：4186 三角面 / 2105 顶点，`is_closed=True`、开放边界 0；包围盒 origin (0,0,128.5)、extent (38,38,128.5)。
- UV：XAtlas 展开，148 个岛、覆盖 61%、重叠 0%、约 2.64 texel/cm（1K）。
- 碰撞：`generate_collision` 以凸包（ConvexHulls，最多 8 个）生成，资产已有 BodySetup。
- 材质槽 0 指向 `M_Plaster`，材质 3 个表达式，BaseColor 与 Roughness 均已连接。

## 已知边界

- 网格由 8 个**独立闭合壳体**叠加而成（各构件未做并集），`connected_components=8`。外观不受影响；如需单一流形可再跑 `SelfUnion`，或用 `VoxelSolidify`（会丢 UV）。
- 本次只做几何、UV、碰撞与材质，**没有渲染、没有放进关卡、没有做视觉验收**。
- 柱式为简化多立克式；未做卷杀（entasis）、柱头涡卷或更精细的凹槽圆底。

## 摆入主场景（2026-09-15 追加）

用户要求摆进"home 主场景"。工程里没有名为 Home 的地图；默认启动图与游戏默认图都是 `/Game/GameMaps/DayNight_Lighting`，且它正是当时打开的关卡，故按此理解摆放。

脚本 `place_column_in_home.py`：找 `Floor` 取顶面高度（origin z=-20、extent z=20 → 顶面 z=0），以出生点 `PlayerStart_SceneTest (-0.06, 0.03, 102)` 为基准偏移 (600, 600)，用 Vibe3D 的 `SpawnStaticMeshActor` 落位，然后保存关卡。

| 项 | 值 |
| --- | --- |
| 关卡 | `/Game/GameMaps/DayNight_Lighting`（PersistentLevel） |
| Actor 标签 | `RomanColumn_Home` |
| 位置 | (599.94, 600.03, 0.00)，包围盒 z 0–257 |
| Actor 数 | 27 → 28 |
| 保存 | 成功 |

邻近检查（800 cm 内）：`TraversalTest_Low_Sign` 180.7 cm、`TraversalTest_Low` 210.0 cm 最近，其余为 StairWalk / MonsterNavigation 测试件；柱子半径 38 cm，无重叠。该关卡本身是系统测试图（Floor + 天气管理器 + 通行/楼梯测试件），不是野外大场景——若"home 主场景"指别的地图，改一处偏移即可重摆。

## 写实版与柱廊（2026-09-15 追加）

用户要求"优化细节尽量写实，然后摆成柱廊"。作者脚本 `build_column_detailed.py`、`place_colonnade.py`。

### 写实化改动

| 项 | 初版 | 写实版 |
| --- | --- | --- |
| 柱础/柱头 | 圆柱+圆锥+圆环堆叠 | **旋成体轮廓**（`append_revolve_polygon`）：柱础含凹弧与圆环曲线，柱头钟形为曲线放样 |
| 柱身 | 直筒 Ø44 | **带卷杀**：底 21.4 → 中下段鼓起 22.05 → 顶 20.6（厘米半径，25 段采样） |
| 凹槽 | 矩形刻槽（`cut_groove_along_polyline`） | **圆凹槽 20 条**：20 根圆柱合成单一刀具网格，一次布尔减 |
| 边角 | 无 | `compute_polygroups` + `bevel_polygroups` 倒角 0.12 |
| 表面 | 无 | 程序化 fBm 噪声贴图 `T_PlasterNoise` → `displace_from_texture` 0.12 cm 微起伏 |
| 面数/高度 | 4186 面 / 257 cm | 12098 面 / 265 cm |

材质升级为 `M_Plaster_Detailed`：噪声同时驱动**颜色**（石膏白 0.88/0.86/0.82 ↔ 灰脏 0.63/0.60/0.55）与**粗糙度**（0.66–0.84）插值，取代原纯色常量。

### 柱廊

| 项 | 值 |
| --- | --- |
| 柱列 | 6 根 `Colonnade_C01..C06` |
| 间距 | 300 cm（约 4 个柱底直径） |
| 位置 | x = 600 / 900 / 1200 / 1500 / 1800 / 2100，y = 600，z = 0 |
| 额枋 | `Colonnade_Entablature` @ (1350, 600, 265)，跨度 1620 cm |
| 额枋构造 | 额枋 16 + 檐壁 14 + 檐口 9（带出挑），资产 `SM_Colonnade_Entablature` |
| 复用 | 原先那根单柱被复用为 C01 并换成写实网格，未留多余柱子 |
| 关卡保存 | 23:43:48，`DayNight_Lighting.umap` 0.79 MB |

### 本次边界

- 仍未渲染、未做视觉验收；写实程度需用户判断。
- UV 覆盖率偏低（XAtlas 1086 岛、覆盖 37%、重叠 0.004%、2.05 texel/cm）：凹槽与倒角把岛切碎。若要烘焙贴图，建议先 `repack_uv` 或改用 PatchBuilder。
- 柱头为简化多立克式，未做三陇板/檐壁浮雕；凹槽端部未做半圆收口。

## 缺陷修复：柱体镂空/间隙 与 顶梁碰撞（2026-09-15 追加）

用户报告两处缺陷，脚本 `fix_column_seams_and_entablature_collision.py`。

### 一、镂空与间隙

根因两条，都在我上一版脚本里：

1. `append_revolve_polygon` 的剖面**没有回到中轴**（起点 r=38、终点 r=22.2），旋成结果是**开口的旋转面**，不是封闭实体。
2. 各段**端面刚好相接**（都从 z=12 / 30 / 230 / 252 起），共面面片之间露缝。

修法：

- 每个剖面首尾补 `r=0` 的中轴点 → 旋成封闭实体；
- 各段改为**重叠 0.5 cm**（如柱础 11.5–30.5、柱身 29.5–230.5）；
- 整体执行 **`self_union`**（自并集）合并为单一流形，再做凹槽布尔。

结果（服务端返回的网格信息）：

| 阶段 | 封闭 | 开放边 | 连通体 | 三角面 |
| --- | --- | --- | --- | --- |
| 合并前 | True | 0 | **6** | 7588 |
| 自并集后 | True | 0 | **1** | 7146 |
| 切槽后 | True | 0 | 1 | 10758 |
| weld + 平面简化后 | True | 0 | 1 | 7060 |

顺带改善：UV 从 1086 岛 / 覆盖 37% 变为 **204 岛 / 覆盖 51%**，重叠 0%、3.04 texel/cm。

### 二、顶梁碰撞

根因：`save_mesh_to_static_mesh` 的 `enable_collision=True` **只是开关**，碰撞几何必须显式生成。柱子当时调了 `generate_collision`，额枋漏了。

修法：`generate_collision(SM_Colonnade_Entablature, "AlignedBoxes", ...)`——梁用对齐盒最合适。

### 验证方式：场景内射线

BodySetup 的形体数组在 Python 里不暴露，所以改用功能验证（编辑器世界 `line_trace_single`）：

| 射线 | 结果 |
| --- | --- |
| 外部 → 柱身（x=600, z=150） | 命中 x=579.5 ≈ 柱身表面半径 20.5 ✔ |
| 梁下方 → 梁底 | 命中 z=265 = 梁底 ✔ |
| 梁上方 → 梁顶 | 命中 z=304 = 梁顶 ✔ |
| 空白处对照 | 无命中 ✔ |

摆好的 7 个 Actor 引用的是同一份资产，资产更新后关卡内即生效，无需重摆。

## 大理石地砖与矮柱围栏（2026-09-15 追加）

用户要求：建大理石地砖、先看 Fab 仓库里的材质包、再加低矮的小罗马柱围栏。脚本 `retry_marble_with_disk_checks.py`。

### Fab 材质包盘点

Fab 库 20 个条目**没有大理石／石材瓷砖材质包**；与石材相近的只有 `Nordic_Beach_Rocks`、`Shoreline_Beach_Rocks`、`Small_Pebbles_Ground`（岩石/砾石）、`Automotive_Substrate_Materials`（Substrate 示例）、`Water_Materials`、`Easy_Building_System_V10`。

工程内确实存在大理石资产（`ColdSteelUI/Warehouse20260909/.../Materials/White_Marble_PBR`、`Textures/marble_albedo`），但**不在资产注册表里**：`load_asset` 返回 None，同步重扫也无效，因此本轮未采用。改为程序化大理石。

### 程序化大理石材质 `M_MarbleTiles`

两张 Vibe3D 程序化 fBm 噪声贴图：

| 贴图 | 参数 | 用途 |
| --- | --- | --- |
| `T_MarbleVeins` | 1024², 4 格, 6 阶, 0.62 | 脉络，驱动颜色插值 |
| `T_MarbleDetail` | 1024², 26 格, 3 阶, 0.45 | 细节，驱动粗糙度插值 |

颜色：象牙白 (0.93, 0.92, 0.90) ↔ 灰蓝脉络 (0.52, 0.53, 0.58)；粗糙度 0.16–0.34（抛光感）。均为具名参数，可在材质实例里调。

### 地砖网格 `SM_MarbleFloorTiles`

1800 × 800 × 5 cm 底板，`cut_groove_along_polyline` 切 24 条缝（100 cm 网格、缝宽 1 cm、深 1.2 cm），平面投影 UV（缩放 1/400，即纹理每 4 m 重复一次，避免逐砖重复）。三角面 110216。碰撞：AlignedBoxes。

**注意：这张地板 4.16 MB / 11 万面偏重**——缝是几何体而非贴图，若要减面建议改贴图缝或跑平面简化。

### 矮柱与栏杆

| 资产 | 构造 | 数据 |
| --- | --- | --- |
| `SM_RomanBaluster_Small` | 底板 26² + 旋成体柱础/柱身/柱头 + 顶板 24² | 高 86 cm，SelfUnion 后 **单一流形**、开放边 0、1908 面 |
| `SM_Balustrade_Rail` | 梁 1600×20×8 + 顶板 1620×26×5 | 两段（下 z=12、上 z=80.5） |

材质均复用 `M_Plaster_Detailed`，与柱廊一致。

### 场景布置（DayNight_Lighting）

| Actor | 位置 |
| --- | --- |
| `MarbleFloor_Colonnade` | (1350, 550, 0.2)，z 0–5 |
| `Baluster_01..11` | y=930，x=600 起每 150 cm 一根，z 0–86 |
| `BalustradeRail_Bottom` / `_Top` | (1350, 930)，z 12–24 / 80–93 |

共 14 个 Actor，关卡 Actor 总数 48；关卡已保存（23:56:49，0.83 MB）。

### 保存事故与修正

首轮大理石构建报告"Created/Saved"成功，但**磁盘上没有文件**，后续按路径加载全部失败（连早先的 `M_Plaster_Detailed` 也读不到）。排查：PIE 未运行、编辑器进程未变；引擎日志 `LogSavePackage` 自 23:45:47 后无记录。重跑时先做**最小保存探针**（存一个盒子并检查磁盘），确认保存管线恢复后再重建全部内容，并逐步校验磁盘存在性与时间戳——本轮 16 步全部通过，资产与关卡均已落盘。

更正：上一版说明中"柱子缝修复与顶梁碰撞仅存在于内存"的判断有误——那两处修改在 23:45:47 已正常写入磁盘；未落盘的是 23:56 之前的那一轮大理石资产。探针资产 `SM_SaveProbe` 已在确认后删除。

## 清理测试障碍物与基石贴地（2026-09-16 追加）

脚本 `clean_scene_and_seat_balustrade.py`。

**删除测试障碍物**：移除 8 个 `TraversalTest_*` Actor——彩色块 Low 60×400×80、Medium 60×400×120、High 200×400×180、Platform 400×500×100，以及 4 个 `TextRenderActor` 标牌。场景 Actor 数 48 → 40。保留 `Floor`、`BP_FPS_DayNightManager`、`PlayerStart_SceneTest`、`MonsterNavigation` 与三个 `RecastNavMesh`（导航基础设施，非障碍物）。`StairWalk_*` 共 12 个属楼梯测试梯架而非彩色块，**本轮未删**，待用户确认。

**围栏基石贴地**：根因是**大理石地板顶面在 z=5.2 而不是 0**，原围栏按 0 摆放，导致原底梁悬空约 6.8 cm、矮柱底部陷入地板 5.2 cm。修法：新建连续基石 `SM_Balustrade_Plinth`（1620×30×12，AlignedBoxes 碰撞，石膏材质），删除悬空的原底梁，矮柱整体坐于基石之上。

射线验证后的层叠关系：

| 构件 | z 范围 |
| --- | --- |
| 大理石地板 | 0.2 – 5.2 |
| 基石（新增） | **5.2 – 17.2**（贴地） |
| 矮柱 ×11 | 17.2 – 103.2 |
| 顶梁 | 103.2 – 115.7 |

关卡已保存（23:59:56，0.81 MB），`SM_Balustrade_Plinth.uasset` 已落盘（14.7 KB）。

## 接入建造面板构件（2026-09-16 追加）

用户要求把**罗马柱**和**矮栏杆罗马柱**加入建造组件。作者脚本 `add_panel_components.py`，只读盘点脚本 `inspect_prefab_palettes.py`。

### 先修掉的调色板错位

`UVoxelBuildComponent` 默认加载 `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`，而 9-16 上午那次 7 条注册写进了父目录的初版 `/Game/Building/Voxels/DA_VoxelBuildPalette`（`register_palette_prefabs.py`、`apply_stone_material_and_palette.py`、`wrap.log` 都是这一份）。活动调色板的 `components` 实际是 **0**，所以面板的「构件」页一直是空的。本轮把两根柱子写进**活动**调色板；初版调色板保持原样，其中 7 条（柱／围栏整体段／体素块 ×2／凉亭 ×3）目前不被任何组件引用。

### 本轮写入的构件

| 稳定 ID | 名称 | 网格 | 20 cm 占格 | 网格实际尺寸 | 材质 |
| --- | --- | --- | --- | --- | --- |
| `roman_column` | 罗马柱 | `SM_RomanColumn_Detailed` | 4 × 4 × 13 | 80 × 80 × 260 cm | `M_RomanStone_V2` |
| `baluster_small` | 矮栏杆罗马柱 | `SM_RomanBaluster_Small` | 2 × 2 × 5 | 40 × 40 × 100 cm | `M_Plaster_Detailed` |

两者的占格都与网格包围盒**逐轴相等**（脚本内已做 `OK / MISMATCH` 自检并打印），所以放置时按 20 cm 格吸附不会出现半格偏移；材质取各自网格当前槽位 0 的材质，放置后外观与案例里摆进场景的那批一致。

### 保存通道与证据

- 编辑器正开着该资产，外部进程保存会静默失败，因此脚本走**运行中编辑器**的 Python 远程执行通道。
- `unreal.EditorAssetLibrary.save_*` 在远程执行上下文里返回 `False`（编辑器处于 PIE 时更明显），可用的保存入口是 `unreal.EditorLoadingAndSavingUtils.save_packages`。此结论会随编辑器状态变化，写入前仍要按磁盘时间戳复核。
- 证据：`save_packages=True`；同进程读回 2 条；关卡**外部**看到的 `DA_VoxelBuildPalette.uasset` 由 3241 B / 17:19:15 变为 4512 B / 17:19:32；直接扫描该文件字节，`SM_RomanColumn_Detailed`、`SM_RomanBaluster_Small`、`M_RomanStone_V2`、`M_Plaster_Detailed`、`roman_column`、`baluster_small` 均存在。

### 边界

- 面板在**进入建造世界时**读取一次调色板内容，已经在 PIE 里的话需要重新进入世界才会看到新增构件。
- 本轮只写数据资产并读回，没有在游戏里点选放置、没有截图；构件是否摆得正、碰撞和手感如何由用户测试。
- 初版调色板里的围栏整体段、体素块、凉亭三件**没有**一并搬过来（用户本次只要两根柱子）；需要的话把 `register_palette_prefabs.py` 的入口指向活动调色板再跑一次即可。

## 大理石体素（2026-09-16 追加）

用户要求：「体素栏新加入一个新的体素，大理石体素，就用罗马柱的材质做一个 20*20cm 的体素块」。脚本 `add_marble_voxel.py`，写入活动调色板 `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette` 的**材质**列表：

| 稳定 ID | 名称 | 表面材质 | 物理参数 |
| --- | --- | --- | --- |
| `marble` | 大理石 | `M_RomanStone_V2`（罗马柱材质） | 密度 2600 kg/m³、抗压 3,000,000 Pa、抗拉 12,000 Pa、抗剪 40,000 Pa、耐久 500、15 J/点（**显式 override**，与代码里 `stone` 的取值一致） |

两点依据：

1. 体素表面生成器自己写**世界投影 UV**（`P[轴]/80`），而 `M_RomanStone_V2` 是纯 UV0 材质（参数为 `StoneNoise` / `StoneDetail` / `StoneBody` / `StoneDirt` / `StoneRoughnessMin|Max`，无 WorldPosition 节点），所以罗马柱材质可以直接铺在 20 cm 体素块上，不需要另做材质。
2. `UVoxelBuildPalette::Physical()` 只对 `id == "stone"` 走石材数值，其余 ID 落到默认（木材）数值。新 ID 若不写 override 会**悄悄变成木材**，所以条目自带显式物理参数。

数量键同步改成「当前分类第 N 项」：面板里 1-9 选当前分类第 N 张卡（材质 1 木材 / 2 石头 / 3 大理石）；建造中 1-3 是材质、4-9 是构件。已通过编辑器内 `LiveCoding.CompileSync` 热补丁生效（17:33:18 `Live coding succeeded`）。

证据：`save_packages=True`；读回 3 条材质；外部看到 `DA_VoxelBuildPalette.uasset` 由 4512 B / 17:19:32 变为 4973 B / 17:32:12。未在游戏里铺过，实际贴图尺度由用户测试。
