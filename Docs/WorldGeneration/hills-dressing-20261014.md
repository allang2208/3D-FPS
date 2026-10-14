# 丘陵铺景低成本档（Phase 1）—— 2026-10-14

纯存量资产复用的一轮密度与氛围提升，没有新增外部采购。所有改动都挂在既有
PCG 层与雾/远景体系上，不引入新的流送阶段或运行时子系统。

## 改动清单

### 野花（草地层第 3 pass）
- `TemperateHillsGrass.cpp`：Pass 循环扩为 0..2，新增花色 pass。间距
  `MeadowFlowerSpacingCm`（默认 380 cm）、覆盖 `MeadowFlowerCoverage`（0.40）。
- 花色有自己的 TileKey 盐（1431）与种属盐（1371），密度由扭曲后的
  Meadow×Tuft 复合场驱动，树荫下抑制 85%（花色是草甸物种，不进林冠）。
- CandidateId 低字节第 2 位 pass 标记 `0xC0`（点缀草为 `0x80`、主草 0）。
- `IsGroundCoverMesh` 扩展覆盖 `MeadowFlowers`：弹坑/铲挖清场连同野花一起清。

### 林下地表（岩石层新增 pass）
- 新文件 `TemperateHillsDressing.cpp`：`GetForestFloorPlacements`。
- 36 m 枚举瓦片，倒木/根系混排（根系约 30%），森林权重驱动密度，
  `ForestFloorCoverage` 默认 0.50。坡度上限 N.Z≥0.85，路径 7 m 与河岸排除。
- CandidateId 高位 `0x2000..`；开采安全由现有解析器保证（>500 cm 实例半径
  拒绝，小件解析为通用石块）。

### 崖壁（岩石层新增 pass）
- `GetCliffPlacements`：52 m 瓦片，仅落在 N.Z∈[0.40,0.78] 的陡坡且
  偏干燥/岩性的地表域，法线 XY 朝向下坡 + 随机偏航抖动，基底下沉 14%。
- CandidateId 高位 `0x1000..`，`CliffCoverage` 默认 0.55。

### 远景树冠（Backdrop 工作线程扩展）
- `FResult` 增加 `Canopy`/`CanopyMesh`，在 `Build` 里以 140 m 间距沿
  远景环带（|max(X,Y)| ∈ [Half+40 m, OuterHalf·0.55]）按同一森林噪声场
  挑选候选；纯数学，无线程安全问题。
- `SpawnBackdropCanopy` 在 `Submitted==3`、重置 `S.Result` 前消费：
  每个用到的网格一个 HISM（无阴影、无导航、无碰撞、无距离场）。
  `EndBackdrop` 同步销毁。预算 `BackdropTreeBudget` 默认 1400 实例。

### 河道薄雾（复用谷底雾管线）
- `BuildValleyFog` 的雾体生成提取为共享 lambda；新增以河道中心线点序号为
  键的 `RiverFog` 池（上限 2，玩家 ±140 m 内，沿河间距 ≥38 m）。
- 体块沿流向定向（`(-Side.Y,Side.X)`），脚印 2600×700×150，
  密度 `RiverMistDensity` 默认 0.24，沿用相同的淡入/淡出/销毁半径。

### 流送预载
- Stage 0 增 `MeadowFlowers`；Stage 2 增 `FallenLogs`/`ForestRoots`/`Cliffs`；
  Stage 7 增 `BackdropTrees`。空数组表示该 pass 关闭，不参与 readiness 门槛。

## 资产来源（全部为本地已购存量）
- 野花：`Content/PN_FoliageCollection`（Fab 植物合集本地副本，Meshes/Materials/
  Textures 已按目录整体拷入，约 372 MB；>5 MB 不进 git）。
- 倒木/根系/崖壁/远景树：`Content/RuralAustralia` 静态网格复用。

## DA 填充
- `Tools/WorldGeneration/build_hills_dressing.py` 备份并写入
  `DA_TemperateHillsStreaming` 的新字段（野花 16 种、倒木 4、根系 1、
  崖壁 8、远景树 6）；标量全部保留代码默认值。
- 运行：`UnrealEditor-Cmd FPSGAME.uproject -run=pythonscript -script=Tools/WorldGeneration/build_hills_dressing.py -nullrhi`

## 状态
- 代码已写完但**未经编译与运行验收**：交付时本机 FPSGAME 编辑器处于打开
  状态，合并编译与 DA 脚本执行需在其关闭后进行。
