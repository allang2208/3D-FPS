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

## 矮栏杆罗马柱古典化升级（2026-09-17 追加，v2 已被 v3 取代）

用户确认方向后对 `SM_RomanBaluster_Small`（面板 ID `baluster_small`）做模型优化升级。**当前磁盘版本为 v3**（`upgrade_baluster_v3_20260917.py`，19:39 落盘 491,146 B）。作者脚本沿革：v2 `upgrade_baluster_20260917.py`（有黑块回归，保留作记录）→ v3。

### 升级内容（v1 → v3）

| 项 | 9-16 版（v1） | v3 |
| --- | --- | --- |
| 柱身剖面 | 4–6 点直边收分圆台 | 56 点古典花瓶式：下 torus 环（r19.25）→ 凹弧 scotia → 鼓腹（r17.8，带收分）→ **双 astragal 珠环** → echinus 外翻 |
| 凹槽 | 无 | 16 条浅圆凹槽（Ø3 刀具 @ R17.8，z 35–67），只在鼓腹段切入，两端自然淡出 |
| 倒角/微位移 | 无 | polygroup bevel 0.12 + `T_Stone_V2_Detail` 置换 0.10 |
| 旋成分辨率 | 48 | 64 |
| 材质 | `M_Plaster_Detailed` | **`M_RomanStone_V2`**（槽 0 + 调色板 surface，家族统一） |
| 面数 | 约 0.9–1.9k | 13,648 |

### v2 黑块回归与根因

v2 曾把三个壳体 `self_union` 合并（无头环境返回 success、单流形），用户在引擎里看到**柱身黑色块**。v3 复制 `rebuild_in_editor.py` 的已验证契约：**不做并集**，壳体间 0.5 cm 重叠各自封闭。对 v3 的独立进程网格法证（`dump_baluster_obj.py` 导出三角面汤）：存储法线与环绕方向 **100% 一致、零翻转面片**，体积 102,374 cm³ 与引擎读数一致，按存储法线着色无任何黑块。结论：v2 黑块来自无头 `self_union` 对焊接面法线/环绕的破坏。

**教训**：无头环境 `self_union` 即使返回 success 且拓扑封闭，也可能破坏法线方向；多壳体重叠方案是首选，与其 9-16 `rebuild_in_editor.py` 一致。

### 体素契约保持不变

bbox 恰好 40×40×100、pivot 底面中心、z=0、占格 2×2×5；剖面最大半径 19.25 < 20。

### 证据

- 磁盘：`SM_RomanBaluster_Small.uasset` 491,146 B / 19:39；`Rounded/DA_VoxelBuildPalette.uasset` 19:38（surface=`M_RomanStone_V2`）。
- 进程内 v3 构建：`RESULT: PASS`（8 步 0 失败，封闭、开放边 0、3 壳体、bbox 40×40×100）。
- 下一进程（dump 运行）读回：6828 顶点 / 13,648 面 / closed / 3 comps。
- 离线渲染 `preview_20260917/v3_shading_stored.png`、`v3_front_stored.png`：真实资产网格按存储法线着色，无黑块。
- 碰撞：ConvexHulls(8) 重建。

### 边界与遗留

- **保存事故重演**：19:37 首次 v3 运行时用户编辑器仍开着并持有该资产，网格保存被静默吞掉（调色板却落盘了）；编辑器关闭后 19:39 重跑才真正落盘。验证必须看磁盘时间戳，进程内 success=True 不算数。
- 真实引擎画面截图脚本 `preview_engine_20260917.py` 已就绪（SceneCapture2D + 显式 `capture_scene()` + `export_render_target`；`take_high_res_screenshot` 与 HighResShot 控制台在远程执行下均不产文件）。PIE 运行中会截到黑图，需在非 PIE 状态跑：`python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/preview_engine_20260917.py`。
- 材质为家族统一的 `M_RomanStone_V2`（BaseColor 噪声插值 + 粗糙度，无法线贴图）。若要更精致的表面，可为该材质加"高度转法线"链，但 XAtlas 岛间会出缝，需先离线烘焙平铺法线贴图——待用户确认再动。
- 踩坑记录：Git Bash 给 `UnrealEditor-Cmd.exe` 传反斜杠路径会静默失败（进程未启动、无任何输出），统一用正斜杠路径。

## 栏杆套件接入建造调色板（2026-09-17 晚追加）

用户要求把好看的罗马栏杆融入建造系统。代码事实（`VoxelBuildPalette.h` / `VoxelBuildWorldPrefab.cpp`）：预制构件支持 90° 旋转（`ComponentYaw`+`RotatedFootprint`）、无支撑校验（顶梁可悬空跨放）、占格不重叠即可放置——**接入零代码，只写调色板数据**。

### 新建网格

| 资产 | 尺寸 | 说明 |
| --- | --- | --- |
| `SM_RomanRail_100/_200/_300` | 100/200/300 × 40 × 40 cm | 圆弧顶梁，截面**逐点复刻** `SM_BalustradeSegment_20` 的模压梁（用户在游戏中认可的样式），20 格对齐，`M_RomanStone_V2` |

### 调色板新增（活动 `Rounded/DA_VoxelBuildPalette`）

| 稳定 ID | 名称 | 占格 | 网格 |
| --- | --- | --- | --- |
| `balustrade_rail_100/200/300` | 罗马栏杆顶梁 1/2/3米 | (5|10|15)×2×2 | `SM_RomanRail_*` |
| `balustrade_segment` | 罗马栏杆整体段 2米 | 10×2×8 | `SM_BalustradeSegment_20` |

### 门构件字段回归与修复

当日早些时候的调色板重建脚本只复制了 `FVoxelBuildPrefab` 9 个字段中的 6 个，**抹掉了门构件的 `actor_class`/`actor_offset_cm`/`material`**（门会退化成静态方块、不能 E 键开）。`integrate_railing_kit_20260917.py` 改为全字段复制并按 `add_door_prefab_entries_20260917.py` 的表恢复 4 扇门。教训：**重建 USTRUCT 数组必须拷贝全部字段**，新增字段后旧脚本会静默丢数据。

### 证据

- 顶梁磁盘：20:57 落盘（首版剖面 X 未居中被否，60 宽→40 宽修正后经编辑器通道重存）。
- 调色板磁盘：9,374 B / 20:59；下一无头进程读回 10 条：4 门 `actor_class` 全部恢复、4 栏杆件占格尺寸自检 OK。
- 首次无头写调色板失败（Error 32 文件共享冲突）：**运行中的编辑器持有调色板**；改走编辑器内远程执行通道（9-16 先例）成功。

### 玩家用法

- 整体段连排：`罗马栏杆整体段 2米` 沿 20 格铺开，端面截面一致，天然拼合成连续栏杆。
- 自由组合：`矮栏杆罗马柱`（2×2×5）按 100/200 cm 间距摆 → `顶梁 1/2/3米` 放柱顶上一行（占格不重叠、可悬空），旋转 90° 换方向。
- 遗留可选：拐角/末端收口件、两柱间自动桥接顶梁（需写代码）、材质法线贴图。

## 建造世界实装替换（2026-09-17 深夜追加）

用户要求删掉游戏里现存的手砌体素栏杆，换成新构件，柱间空隙用体素块拼接。目标存档 `Voxel20_EA319301D380398C3E2B85F8D5D81163.sav`（WorldKey `ColdSteelPlayer|DayNight_Lighting`）。

### 旧布局 → 新布局

- 旧：305 块大理石体素手砌（x27..36，y-36..-18，台阶状），0 预制件——"方形顶梁"问题的本体。
- 新（同区域，x 格 28..29，沿 y）：
  - `baluster_small` ×3，锚点 y=-36/-27/-18（180 cm 节奏，占格 2×2×5）
  - 大理石体素填缝 ×56：两段 7 格间隙 × 2 格宽 × 2 格高（z 0..1，与柱础 40 cm 齐平，视觉上把柱子连成整体）
  - `balustrade_rail_200` ×2，z 格 5（柱顶上一行），y=-36 与 -26，400 cm 闭合无重叠

### 踩坑记录（重要）

1. **无头 commandlet 放不了体素**：`ScenePlacementAllowed` 的地面锚定射线在 commandlet 世界全部失败（`VOXEL_REJECT stage=support`、格子无锚），即使 `load_map` 加载了 DayNight 也一样；而预制件（`PlacePrefab`）不做地面/支撑校验所以能放。**体素操作必须在活着的 PIE 建造世界里做**——用户会话里 305 块体素本身就是证明。
2. **活会话自动存档覆盖**：用户在建造模式时，其会话的 `TickPersistence` 会把内存旧状态写回存档，无头进程的 `Save()` 结果几分钟后即被覆盖（三次实测）。结论：改建造世界必须改**活世界**（远程执行进 PIE）或确认用户完全退出。
3. 最终路径：轮询远程执行通道 → 检测 PIE 内 `VoxelBuildWorld` Actor → 就地改建（`RemovePrefab`/`EditCells(None)` 清场 → `PlacePrefab` ×5 → `EditCells` 填缝 ×56）→ `Save()`。

### 证据

存档 1,619 B / 21:44

## 地图围栏换装（2026-09-17 深夜追加，用户指认的才是真目标）

用户发截图指认：要换的"现在的栏杆"是 **DayNight 地图里 y=930 的 8 根 `BalustradeSegment_20` 整体段**（编辑器视口可见那排），不是建造世界存档。此前两轮（建造世界改建）没动这排，用户自然"看不到变化"。教训：**"游戏里现有的 X" 以用户截图为准，先确认指哪一层**。

### `replace_map_fence_20260917.py`（无头改图 + 保存）

- 删除 8 根旧整体段（x 500..2100，y=930）；`MarbleFloor_Colonnade` 平台顶 z=20（运行时读 bounds，别写死 5.2）。
- 新围栏 144 Actor，同位置同节奏：
  - `SM_RomanBaluster_Small`（v3）×8，x=600..2000 每 200，z=20（贴平台顶）
  - `SM_RomanRail_200` ×8，x=500..2100 通长覆盖，z=120..160（圆弧截面）
  - 20 cm 体素块 ×128（`/Engine/BasicShapes/Cube` 缩 0.2 + `M_RomanStone_V2`），柱间 7 段 160cm 间隙 + 两端 80cm，2 层（40 cm，与柱础齐平）
- 命名 `RomanFence_*` 便于以后整体选中/替换。
- 保存：`LevelEditorSubsystem.save_current_level()` 无头可用（返回 True）；umap 857 KB → 1,054,351 B / 22:07。

### 证据

下一进程重新加载 umap：columns=8 rails=8 voxel_cubes=128 old=0；column_01 x 580..620 / z 20..120；rail_08 x 1900..2100 / z 120..160。

另：建造世界存档（`Voxel20_EA31....sav`）里的新栏杆（3 柱+2 梁+56 缝）与本图围栏是两处独立内容，均保留。
：含 `baluster_small`、`balustrade_rail_200`、恰好 56 处 `marble`。脚本 `rebuild_railing_20260917.py`（无头版，含诊断）、`rebuild_live_20260917.py`（活世界版，最终采用）、`dump_build_world.py`（布局 dump）。

## 凉亭 v2：更大跨度 + 真半球穹顶 + 140 凹格（2026-09-17 追加）

用户要求：场地扩大（原来太小）、穹顶要真圆顶并带浮雕（现在像圆锥）、参考 GitHub 上的建筑资料。作者脚本
`build_pavilion2_20260917.py`（建模+摆场）、`integrate_pavilion2_20260917.py`（柱环整体件+调色板）、
`render_pavilion2.py`（离线几何自查渲染）、`probe_*.py`（根因与约定探针）。

### 旧穹顶为什么是圆锥（根因，不是感觉问题）

离线导出旧 `SM_PavilionDome_20` 的三角面汤后按 z 分桶：**z=20 与 z=286 之间一个顶点都没有**——外壳是一条直弦，
字面上的圆锥。根因是最初 `build_pavilion.py` 里的 `self_union(dome, True, True)`：两个布尔参数实为
`bFillHoles` / `bTrimFlaps`，`bTrimFlaps=True` 会把弧面塌成弦。同一剖面分阶段实测（`probe_bisect_dome.py`）：

| 阶段 | 三角面 | z 60..260 的顶点环 |
| --- | --- | --- |
| 原始 revolve（剖面没变） | 6144 | 有（69/92/116/138/160…） |
| + `self_union(True, True)` | 2112 | **无**（直弦） |
| + `self_union(False, False)` | 5857 | 有 |
| + auto_uv / 保存 | 不变 | 不变 |

结论：**无头几何不要用 `self_union(True, True)`**；至少传 `(False, False)`，而本工程既有的"多壳重叠、不并集"
做法（[矮栏杆 v3](#矮栏杆罗马柱古典化升级2026-09-17-追加v2-已被-v3-取代)）更稳。

### 新尺寸与建筑依据（按万神殿实测数据 1:6.1 缩放）

| 构件 | 网格 | 20 cm 占格 | 实际尺寸 |
| --- | --- | --- | --- |
| 台基 | `SM_RomanPavilionBase_20` | 48 × 48 × 1 | 960 × 960 × 20 |
| 柱环（10 柱 + 额枋，整体件） | `SM_RomanPavilionColonnade_20` | 44 × 44 × 17 | 880 × 880 × 340 |
| 额枋环（单件，可单独用） | `SM_RomanPavilionArch_20` | 44 × 44 × 4 | 880 × 880 × 80 |
| 穹顶 | `SM_RomanPavilionDome_20` | 40 × 40 × 20 | 800 × 800 × 400 |

- 平面：柱环半径 360（10 柱，柱距 226）、台基半径 480、额枋内缘 320 / 面 400 / 檐口 440、穹顶外半径 400、
  内壳（soffit）360、天窗半径 72。穹顶外缘与额枋面、柱础外缘同处 r=400，是"上下同一竖面"的古典关系。
- 比例：内部直径 720、内部净高 740 ≈ **1:1**——万神殿的规则（起拱在总高一半、顶点等于直径）。
- 凹格：**5 行 × 每行 28 格 = 140**（万神殿实测 140 格），行高按 `Δφ = k·sinφ`（k = 0.78·2π/28）递减，
  这是让穹顶读成穹顶而不是帐篷的关键；顶部留 137 cm **素面穹冠**。格深 13（≈格宽 1/5）、环肋 14、子午肋 16，
  后两者 = 万神殿实测 0.84 m / 1.0 m ÷ 6.1。
- 穹顶默认**封顶**（`CLOSE_OCULUS = True`）：素面穹冠收到顶点，顶面平滑无凸圈。天窗版本仍保留在同一脚本里
  （`CLOSE_OCULUS = False`，天窗半径 72 = 0.20 倍跨度，对万神殿 0.202，外侧带压顶环），需要采光时一行切换。
- 外侧：下半部 3 道**内退**阶梯环（每道 5 cm）+ 天窗圈。凹格在罗马做法里只做内侧（万神殿 141 格全在内）。
- 没能照抄的地方：万神殿阶梯环之所以深，是因为壳厚（5.9 m / 44 m = 13%）；本件壳厚 40 / 720 = 5.6%，
  阶梯一级只能退 5 cm，再深会切穿内壳。这是尺寸缩放带来的硬约束，不是省事。

### 与旧版对比

| 项 | 旧（9-16） | v2 |
| --- | --- | --- |
| 平面直径 | 640（柱环 480） | 960（柱环 720） |
| 柱数 | 8 @ R240 | 10 @ R360 |
| 穹顶 | 直圆锥，2112 面 | 半球壳 + 140 凹格，24288 面（封顶版） |
| 内部面积 | ≈ 18 m² | ≈ 41 m² |
| 内部净高 | 620 | 740 |

### 场景（DayNight_Lighting）

- 旧 11 个 `Pavilion_*` actor 删除，新 13 个 `RomanPavilion2_*`：台基 z=0、10 柱 z=20、额枋 z=280、穹顶 z=360。
- 位置由 (1350, 0) 后移到 **(1350, -400)**：新台基直径 960 会压到大理石地板（地板边缘 y=150），后移后留 70 cm。
- 下一进程读回：关卡 38 actor、13 个新凉亭、0 个旧凉亭；关卡文件 21:55:03 落盘。

### 建造调色板

- 活动调色板 `Rounded/DA_VoxelBuildPalette` 新增 4 条（`pavilion_base` / `pavilion_colonnade` / `pavilion_arch` /
  `pavilion_dome`），共 14 条；四条占格与网格包围盒逐轴相等（脚本自检 OK），4 扇门的 `actor_class` 经整字段复制保留。
- **柱环整体件存在的原因**：10 根柱子的柱心在 R360 圆周上，坐标不是 20 cm 格点（如 291.2 cm = 14.56 格），
  玩家无法徒手摆正——把柱环和额枋合成一件才能保证几何正确。
- 柱环里的柱身经容差简化到 6,422 面（源 32,708，20%），整体件 68,116 面 / 3.73 MB；单件 `roman_column`
  仍是全精度网格，节庆级细节未被牺牲。

### 实测缺陷修复：额枋 pivot 偏移（用户回报）

用户回报两条：穹顶上方多出一圈、穹顶与柱顶之间有间隙。排查（`diagnose_pavilion2_gap.py` 打印每个构件的
**本地**包围盒与每个 actor 的世界跨度）证明是**同一个 bug**：

| 项 | 修复前 | 修复后 |
| --- | --- | --- |
| `SM_RomanPavilionArch_20` 本地 z | **280 … 360**（pivot 在几何下方 280 处） | 0 … 80（pivot 在底面） |
| 额枋 actor（loc z=280）实际跨度 | **560 … 640** | 280 … 360 |
| 柱顶(280) 与穹顶底(360) | **空 80 cm 缺口** | 相接 |

根因：我在建额枋时把**世界高度（280/360）直接写进了旋成剖面**，于是整个网格比它自己的 pivot 高了 280 cm。
两个可见后果都由它引起——柱顶上方空出 80 cm；而那只环飘到 560..640，半径 440 比该处穹顶外表面（346→286）
还大，就从穹顶上半部捅出来，看起来像"穹顶上面多了一圈"。柱环整体件同样用了非 0 基准的局部 z（20 起），
一并改成从 0 起。

**教训**：旋成剖面的 z 必须是构件自己的局部坐标（0 = 构件底面），世界高度由 actor 摆位给出——旧版
`build_pavilion.py` 的环件就是这么做的（剖面 0..40、actor 放 280），我这次偏离了。`publish()` 之后新增
**pivot 自检**（本地 z 必须从 0 起）与**拼装自检**，两者都在 `RESULT: PASS` 的条件里。

### 走不进柱间？入口台阶与预制件摆放的修正（用户回报）

用户回报"不能通过两个罗马柱之间进入凉亭"。排查结论：**柱子不是原因**——凸包/对齐盒碰撞都不会超出网格自身的凸包，
每根柱子的碰撞 ≤ 自己的 80×80 底面，不可能横跨 226 cm 的柱距；把同一批资产在新进程里重新摆一遍再扫（见下），
10 个柱间全部可通行。真正该修的是下面两件事，都已改：

1. **台基从"一级 20 cm"改成"两级各 10 cm"**（`SM_RomanPavilionBase_20` 剖面 `0→480→480,10→466,10→460,20`）。
   角色 `MaxStepHeight = 40`（`FPSGAMECharacter.cpp:187`），一级 20 cm 在地面略有起伏时正好贴着上限；
   两级 10 cm 在哪里都上得去，也更接近罗马台基的多级做法。
2. **预制件摆放的三个陷阱**（都在调色板数据里修掉了，网格没动）：
   - 四件的占格宽度原本各不相同（48 / 44 / 40 格），而建造系统把网格**包围盒居中**放进占格体积
     （`AVoxelBuildPrefabActor::ComputeTransform`）——四件放在同一格会各偏 40~80 cm，叠起来是歪的。
     现在**三件的 X/Y 占格统一为 48 格**，放同一格就自动对齐；Z 仍等于各自网格高度（1 / 17 / 20 格）。
   - `pavilion_arch`（单独额枋环，44×44×4）**从调色板撤下**（脚本里的 `RETIRED` 列表显式删除）：柱环整体件已经含额枋，
     两件同时摆会叠出两个环。网格保留在磁盘上备用。
   - 条目名直接写顺序：`罗马凉亭①台基` / `②柱环10柱(放①上)` / `③穹顶140凹格(放②上)`。

**给用户的现场判断法**：游戏里按 `~` 输入 `showcollision 1`，可直接看到碰撞体——柱间若被某个看不见的体挡住，一眼就能
看出是哪一件、在什么高度。另外建造面板只在**进入建造世界时**读一次调色板，改过的三件要重进世界才会生效。

### 真正堵住入口的是穹顶的碰撞体（用户再回报"还是进不去"后定位）

上一轮我按"柱子碰撞不可能横跨柱距"推理，并在无头进程里扫过射线，结论是"能通行"——**那个结论是错的**，
因为无头 commandlet 里物理查询只认本进程新建的 actor（见下一条），没打中不代表通。本轮改用**运行中编辑器**内的
`Tools/AssetPipeline/ue_python_exec.py` 通道实测（那里的物理是活的），一步就点名了元凶：

| 探针位置（r=42 球体重叠） | 修复前 | 修复后 |
| --- | --- | --- |
| 凉亭中心 z=96（胸口） | `['RomanPavilion2_Dome']` | **nothing** |
| 凉亭中心 z=200 / 300 / 500 | `['Dome']`（含 Arch @300） | **nothing** |
| 柱间通道 r=360 z=96 | `['Floor','Dome','Base','Column_01']` | 只有 `Column_01`（正确） |
| 10 个柱间胶囊扫掠（z=96/130/170） | **0/10 通过** | **10/10 通过** |

根因：`generate_collision` 给穹顶**多塞了一个超大的 sphyl（胶囊）形状**——穹顶网格在 z 360–760，而那个胶囊从
地面一直垂到穹顶，把整个内部和每个柱间全罩住了。台基与柱子的碰撞反而是正常的（台基只在 z=20 命中、柱子只在柱身命中）。

修法：**壳体与环不用生成形状，清空简单碰撞 + `CTF_USE_COMPLEX_AS_SIMPLE`**（三角面自己就是碰撞体：内部通透、
子弹仍打在穹顶上）。这正是本工程建造体素块用的口径（`VoxelBuildWorldMesh.cpp` 的 `CTF_UseSimpleAsComplex`）。
已在运行中的编辑器内改写并保存：台基 `{'box':1}`、柱环 `{'box':71}`（逐柱盒）、柱子 `{'convex':70}`、
穹顶/额枋 `shapes=none + complex-as-simple`。改完必须让场景里的 actor 重建物理状态才生效
（`set_collision_enabled(NO_COLLISION)` → `QUERY_AND_PHYSICS`；该 Python 绑定里没有 `recreate_physics_state`）。

### 凉亭专用圆板柱（用户要求"柱子上下的方形衔接件改成圆形"）

用户指出：柱子上下两块**方形**垫板/顶板与圆形凉亭不协调。只改凉亭用柱，直线柱廊保持原样：

| 项 | 值 |
| --- | --- |
| 新资产 | `SM_RomanColumn_Round_20`（柱身、20 道凹槽、柱头钟形与 `SM_RomanColumn_Detailed` 完全一致） |
| 改动 | 柱础方板（z 0–20）与柱头方板（z 240–260）换成 **Ø80 圆盘**，其余壳体未动 |
| 契约 | bbox 80 × 80 × 260、pivot 在底面、闭合无开口（32,908 面）、碰撞 = 逐壳 7 个盒 |
| 用在哪 | 关卡凉亭的 10 根柱 + 建造调色板 `罗马凉亭②柱环10柱` 整体件；直线柱廊 6 根仍用方形柱 |

做法（`build_round_column*.py` 迭代三次才对）：**按独立壳体选取**——方板是一个独立壳体，用
`select_connected` 打角点 `(38.5, 38.5, 8)` / `(38.5, 38.5, 250)` 正好只在方板内部（圆盘那里是空的，
所以选不中就是自检），删掉该壳体后**用剩余网格的 min/max z 反推方板高度**（20 / 240→260），再补 Ø80 圆盘。
两次踩空的原因记在这里：按 z 分带 + "max|x| > 30"判断方形会把 Ø80 的圆盘也算成方形（圆的 max|x| 同样是 40，
只有**对角半径** 56.5 才区分得出），第一次还因此把柱础和柱头整段误删。

### 结合处收尾：额枋加宽 + 柱础圆盘放大（用户第二轮反馈）

用户看过圆板柱后提了两点，都已落盘：

| 项 | 原来 | 现在 |
| --- | --- | --- |
| 额枋底面外缘 | r 392 | **r 400**——与柱头圆盘边缘（r400）、柱础外缘同处一个竖面，圆盘不再探出 |
| 额枋外廓（柱楣 / 檐壁面） | r 382 / 390 | **r 394 / 400**（都 ≥ 圆盘半径，从外面看不到圆盘边缘） |
| 齿饰带 | 嵌到 r 384–424 | 随檐壁外移，仍压在檐口下 |
| 柱础圆盘 | Ø80 | **Ø90**（柱头圆盘保持 Ø80，已被加宽的梁盖住） |
| 檐口出挑 | r 440 | 不变（檐口本来就该出挑，形成阴影线） |

**几何依据**：柱头圆盘顶面正好在额枋底面（世界 z=280），所以只有**梁底的外缘**需要够宽——一旦底面到 r400，
上面各层即使略窄也不会让圆盘外露。改完再离线渲染确认（`preview_20260917/p2_final_*.png`）。

**写入过程**：编辑器开着时圆板柱与额枋都保存不动（磁盘时间戳停在旧版，仍是"编辑器持有资产"那个现象）；
关掉编辑器后逐个重建即落盘。场景**不需要改动**——actor 引用的是同一批资产路径，重建后自动生效，只需重新加载关卡。
本次落盘：圆板柱 22:57:17（90×90×260）、额枋 22:57:33（880×880×80）、穹顶 22:57:36、柱环件 22:58:01（880×880×340）、
调色板 22:58:01；下一进程读回确认 13 个凉亭 actor 用的正是圆板柱。

### 凉亭与圆底罗马柱做成两个独立建筑组件（2026-09-17 追加）

用户要求：凉亭与圆底罗马柱各做成一个独立构件、归到**大理石**材质的「其他构造」子菜单下，并设计好占格。
作者脚本 `build_pavilion_component_20260917.py`。

| 稳定 ID | 名称 | 网格 | 20 cm 占格 | 网格尺寸 | 归属 |
| --- | --- | --- | --- | --- | --- |
| `pavilion_full` | 罗马凉亭（整体） | `SM_RomanPavilionFull_20` | **48 × 48 × 38** | 960 × 960 × 760 | 大理石「其他构造」 |
| `roman_column_round` | 圆底罗马柱 | `SM_RomanColumn_Round_20` | **5 × 5 × 13** | 90 × 90 × 260 | 大理石「其他构造」 |

- 整体件 = 台基 + 10 根圆板柱（柱身沿用柱环件的容差简化，6,602 面）+ 额枋 + 穹顶合并网格，95,588 面 / 3.3 MB。
  原先的三件（台基／柱环／穹顶）**已退役**——单件一次放置即可，且不必再手算 1／14／18 格的堆叠关系。
- 占格按标准取"网格包围盒 ÷ 20"：凉亭 **逐轴相等**（960/760 都是 20 的整数倍）；圆底柱 90 cm = 4.5 格，
  只能向上取 5 格（取 4 格＝80 cm 比网格还小，会让构件互相穿插），网格因此两侧各留 5 cm、居中放置。
- 两条组件都是**普通构件**（`ActorClass` 为空），材质字段填 `marble` → 只出现在大理石行的「其他构造」里
  （归类规则见体素建造工作流 §4.2；不填就会掉进「其他」分类）。

**预览＝落地（工作流 §3.8 那条坑）**：普通构件的幽灵预览（`UpdatePrefabPreview` 的 else 分支）与落地
（`SpawnPrefab`）**调用同一个** `AVoxelBuildPrefabActor::ComputeTransform`——按**网格包围盒居中**于占格体积，
与 pivot 无关（查看构件的 pivot 在底面还是角上都不影响）。脚本按该公式复算并打印，证据：

| 构件 | 占格 cell | actor 落点 | 网格世界跨度 | 占格体积 |
| --- | --- | --- | --- | --- |
| 凉亭整体 | (0,0,0) | (480,480,0) | x 0–960，y 0–960，z 0–760 | (0,0,0)–(960,960,760) —— **逐轴重合** |
| 圆底柱 | (0,0,0) | (50,50,0) | x 5–95，y 5–95，z 0–260 | (0,0,0)–(100,100,260) —— 两侧各 5 cm |

**又踩到同一个碰撞坑**：合并件生成碰撞后同样带出 `sphyl: 1`（Vibe3D 给圆弧网格补的巨型胶囊，正是先前
堵死凉亭的元凶）。脚本里加了 `strip_stray_shapes()`：清掉 sphere／sphyl／taper 三类，保留逐壳盒子
（台基 1 盒、10 根柱各 1 盒、其余都在 280 cm 以上）。终态 `{box: 73, sphyl: 0}`。

写入前先关编辑器（整体件未落盘时被锁会静默失败）；调色板 12 条已落盘（23:04:18），面板**进入建造世界时**读取，
重进世界即可在「大理石 → 其他构造」看到这两件。

随后按用户要求把**整族罗马构件**都归到大理石行（`group_marble_components_20260917.py`）：方底罗马柱
（`roman_column`）＋大理石栏杆套件（`baluster_small`、`balustrade_rail_100/200/300`、`balustrade_segment`）
由空值改为 `marble`（23:07:42 落盘）。现在各行：大理石 = 罗马柱／矮栏杆罗马柱／大理石门／顶梁×3／整体段／
凉亭整体／圆底罗马柱；石头 = 石门；木材 = 木门；**「其他」只剩铁门（撞开）**。

### 凉亭面板缩略图排查（2026-09-17 深夜）

用户报告「凉亭还没预览图」。面板缩略图由 `VoxelBuildIcons`（GameInstance 子系统）在游戏里实时渲染：
正交取景（最大边长占画面 `IconFillFraction=0.78`、固定 -18/-35 视角）、color 走 `SCS_FinalToneCurveHDR`、
coverage 走 `SCS_SceneColorHDR` 作 alpha，两者交给 `M_WeaponPreviewResolved` 合成。**先怀疑渲染对 960 cm
的大件失效，于是用同一套参数在编辑器内复现**（`probe_icon_capture_20260917.py`，把试件放到 2000 m 高空避免
关卡几何入镜）：

| 试件 | 取景 | color | coverage |
| --- | --- | --- | --- |
| 凉亭（960 cm） | ortho 1231、相机 (-1730,1211,201066) | 出图正常、构图正确 | 干净剪影 |
| 栏杆整体段（200 cm，对照） | ortho 256 | 出图正常 | 出图正常 |

**结论：渲染路径对凉亭有效**，两条通道都能出图，遮罩也合格——所以面板缺图不是渲染失败，而是运行时
「请求／缓存／卡片取用」这一段的时序问题（`Failed` 集合是一次失败即永久拉黑；`RefreshIcons` 每帧轮询
并在无图时重排队的自愈逻辑见 `VoxelBuildWidget.cpp:368`）。

顺带产出**棚拍预览**（`shoot_pavilion_preview.py`，编辑器内临时布光、用完即删、关卡不保存）：
`preview_20260917/pavilion_hero_768.png`（3/4 特写）、`pavilion_card_256.png`（面板同口径 256×256）、
`column_card_256.png`（圆底柱）。原始导出是 16 位 PNG，看图前先转 8 位（`*_8.png`）。

### 本次踩到的新坑（已同步进技能与记忆）

1. **UE 5.8 Python 的 `unreal.Rotator(...)` 构造参数顺序是 (roll, pitch, yaw)**，不是 C++ 的 (pitch, yaw, roll)
   ——`Rotator(10, 20, 30)` 读回 pitch=20 yaw=30 roll=10。按 C++ 顺序传会把径向肋条绕错轴、镜像到起拱面以下
   （实测顶点 z = -356.1）。该旋转下的局部轴：X 沿子午线、Y 切向、Z 法线，模板盒子要"深度在 X、宽度在 Y"。
2. **无头 commandlet 里 `spawn_static_mesh_actor` 不生成 actor**（`LogUtils: Warning: SpawnActorFromObject.
   No actor was spawned.`，Vibe3D 报 handle -1）；用 `EditorActorSubsystem.spawn_actor_from_class(StaticMeshActor)`
   再 `set_static_mesh` 替代（`dump_build_world.py` 早在用这条）。
3. **同一进程里先加载关卡会让调色板 `save_packages` 返回 False 且不落盘**；把调色板写入排在所有关卡操作之前即可
   （`integrate_pavilion2_20260917.py` 的顺序即为此）。
4. 保存仍可能撞 **MoveFile Error 32**（OneDrive/杀软短暂锁住刚写过的 `.uasset`，日志里是 `LogFileManager:
   Warning: MoveFile was unable to move … (Error Code 32)`）。进程内 `success=True` 不算数——`publish()` 现在
   读磁盘时间戳，STALE 时延迟重试。
5. 保存顺序踩坑：一次构建里台基/额枋**磁盘未更新而穹顶更新了**，逐件磁盘时间戳是唯一可信证据。
6. **旋成剖面的 z 一律用构件局部坐标（0 = 底面）**：写成世界高度会让整个网格偏离 pivot，表现为"构件飘在
   半空 + 另一处出现莫名的一圈"。构件建好后先读 `get_bounds()` 的本地 z 是否为 0 起，再摆场。
7. **无头 commandlet 里的物理查询只认本进程新建的 actor**：从 `.umap` 读入的关卡几何**永远不返回命中**
   （连地面都打不中），"射线没打中 = 这里通的"是**假阴性**。**编辑器内的远程通道（`ue_python_exec.py`）则是活的**：
   碰撞判定要在编辑器里做，并且用 `SystemLibrary.sphere_overlap_actors` **点名阻挡者**——该通道里 HitResult 的
   `location`/`hit_actor` 字段读不出来，但重叠查询返回的是 actor 本身，反而更好用。
9. `SV.selection_bounds` 在本绑定里**返回空**（不能用来校验选区）；要验证选区就用 `selection_count` +
   删除后的 `get_mesh_info` 边界反推。`select_connected(handle, name, point)` 打一个"只有目标壳体才包含"的点，
   是拆装多壳体网格最可靠的选取方式。
8. **`generate_collision` 会给圆弧网格塞超大的 sphyl（胶囊）形状**：穹顶的碰撞因此从地面一直垂到穹顶，把整个
   建筑内部堵死（网格本体在 360–760 完全正常）。壳体/环的正确口径是清空简单碰撞 + `CTF_USE_COMPLEX_AS_SIMPLE`；
   逐独立壳的 `AlignedBoxes` 对盒子类构件才是对的。改资产后运行中的 actor 要用
   `set_collision_enabled(NO_COLLISION)` → `QUERY_AND_PHYSICS` 重建物理状态才会生效。

### 验证边界

- 已做（进程内 + 跨进程）：几何自检（凹格射线内外判定、顶点 z 范围恰好 0..400、包围盒 = 占格）、逐件磁盘时间戳、
  下一进程读回关卡、4 条碰撞射线（柱间可通行 / 柱身实心 / 檐口实心 / 中轴命中）。
- 缺陷修复后已复核：4 个构件本地 z 均从 0 起、关卡里 4 段跨度首尾相接（0-20 / 20-280 / 280-360 / 360-760）、
  柱环件本地 z 0..340、调色板 4 条占格自检 OK 且落盘。
- **未做**：引擎内视觉验收、实机走动与光照观感。`preview_20260917/p2_*.png` 是自写 z-buffer 的离线几何自查
  （`render_pavilion2.py`，不经过引擎），只用于确认凹凸格与体量，不代表引擎画面。
