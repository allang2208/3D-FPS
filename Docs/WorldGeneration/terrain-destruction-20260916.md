# 地貌破坏：高度场方案（2026-09-16 现行）

项目决定**不再引入体素地形**，地貌破坏全部在温带丘陵的运行时高度场上完成。本文是现行标准：能做什么、数值规则、性能边界、可调开关和未做的事。体素方案（Voxel Plugin Free Legacy + 局部洞穴测试台）已退役：代码与测试地图归档在 `trash/voxel-terrain-retired-20260916/`（含 SHA-256 清单），调研与接入过程记录在 [voxel-terrain-sandbox-20260916.md](../Rejected/voxel-terrain-sandbox-20260916.md) 与 [Voxel Plugin 安装器登记](../Rejected/VoxelPlugin-installer-20260916.md)。

## 1. 能力边界（高度场的先天限制）

高度场是"每个 XY 只有一个 Z"的曲面，因此：

| 能做 | 不能做 |
| --- | --- |
| 弹坑、铲子挖低、回填抬高、切出台阶/平台、削平坡面局部 | 竖井、洞穴、隧道、悬垂、掏空山体（需要 3D，已决定不做） |

## 2. 玩法规则

| 项 | 规则 |
| --- | --- |
| 火球弹坑 | 命中点按火球半径生成碗形坑：半径 = 效果半径 × `fps.Hills.CraterRadiusScale`（默认 1.5），深度 = 半径 × `CraterDepthScale`（0.4），外圈唇 = 半径 × `CraterRimScale`（0.12）。入口 `TerrainDestruction::CarveCrater`，只有 `ATemperateHillsWorld` 存在时生效（主城静态地板不受影响） |
| 铲子挖掘 | 铁铲（8）左键，**一击一层**：240×240 cm（12×12 个 20 cm 格）整体下降 20 cm，中心对齐 20 cm 世界网格；产出 2 个「泥土」；同一格可继续下挖 |
| 右键回填 | 铁铲（8）右键（工具有手时右键不是 ADS）：同足迹抬高 20 cm，消耗 2 个「泥土」 |
| 瞄准距离 | 铲子用 `fps.Tool.DigReach`（默认 1000 cm）沿屏幕中心射线；斧/镐仍是 3.2 m 触及 |
| 坡面限制 | 沿用表土采集门槛：坡面法线 Z < 0.65（约 49.5°）或河床湿区拒绝；角色本身可行走上限 45° |
| 上层草类 | 每次编辑清除足迹内的草类实例（`Grass / GrassAccents / RiverGroundCover / RiverReeds / RiverBankGrasses`），不动树、岩石、灌木；PCG 流送回草后每 1 s 对玩家 80 m 内的编辑重新清一次 |
| 存档 | `UTemperateHillsSave` Version 3，`Edits` 数组；V2 的圆形弹坑读取时自动迁移，V1 仍可加载 |

## 3. 下沉/抬升上限（你问的"最多沉降多少"）

两个 CVar，单位厘米，都是**相对生成地表**测量：

| CVar | 默认 | 含义 |
| --- | --- | --- |
| `fps.Hills.MaxDropCm` | **400** | 任何挖掘/弹坑最多只能沉到生成地表以下 4 m；到达上限后新的挖掘被拒绝（坑中心剩余深度不足时，弹坑深度会被自动削减到剩余额度），铲子那一格也不再复位进度，下一次挥动提示"此处资源已经采尽" |
| `fps.Hills.MaxRiseCm` | **100** | 回填最多抬到生成地表以上 1 m；到上限时提示"这里已经回填到上限（100 cm），换一处再填" |

数值来源都在这两个 cvar 里（代码只在 `ApplyTerrainStep` / `ApplyCrater` 里做 clamp），改完立刻生效，不需要重编译、也不需要重进地图。

## 4. 性能设计

| 环节 | 做法 |
| --- | --- |
| 编辑影响范围 | 一次编辑只把**覆盖到的 64 m 分块**标脏重建；旧网格保留到新网格碰撞烹饪完成才替换，不会掉进地里，也不会触发整片世界重新流送 |
| 网格精度 | 被编辑的分块网格分辨率翻倍（`fps.Hills.EditMeshBoost`，默认 2；设 1 关闭，代价是坑更方），只有被编辑的分块付这个代价 |
| 高度采样 | `Height()` 里的编辑偏移用**32 m 空间桶**索引（`RebuildEditBuckets`），植被/PCG 采样不会遍历整张编辑表 |
| 法线 | 只在编辑影响范围内用数值法线，其余沿用生成法线 |
| 清草 | 每次编辑清一次 + 每 1 s 对 80 m 内编辑补清；用包围盒早退，草以外一律不碰 |
| 编辑数量 | 每世界最多 256 条编辑，超出淘汰最旧的并把那块地重建回生成高度 |
| 流送 | 沿用丘陵原有的预算（最多 2 个后台网格任务、每帧 1 个网格提交、每帧 1 格卸载），编辑重建走同一条流水线 |

CVar 速查：`fps.Hills.MaxDropCm`、`fps.Hills.MaxRiseCm`、`fps.Hills.EditMeshBoost`、`fps.Hills.CraterRadiusScale / CraterDepthScale / CraterRimScale`、`fps.Hills.CraterDebugLog`、`fps.Tool.DigReach`。

日志：`HILLS_CRATER`（弹坑）、`HILLS_STEP`（每层挖/填）、`HILLS_REFILL`（回填）、`HILLS_GROUND_COVER`（清草数量）、`HILLS_EDIT restored`（读档恢复条数）。

## 5. 未做 / 边界

- 树与岩石不会随坑洼重新落地（PCG 实例不重算），只有新生成的点会用新高度。
- 河道水面网格不随坑洼重建；远景 backdrop 用的是另一套简化高度，不参与编辑。
- 主城 `DayNight_Lighting` 是 40 cm 静态地板，不是地形，火球在那里只留特效。
- 洞穴/竖井类玩法在本方案下不可实现；如以后仍需要，正确做法是整体替换地表后端（自研 level-set + Transvoxel，或付费 VP2），而不是叠加第二套地形。
- 本文件描述的改动**未做运行验收**（按项目规则由用户实机测试）。
