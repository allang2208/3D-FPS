# 树桩可劈 + 幼树偏移再生（2026-09-28）

用户要求两条：

1. **树桩有生命数值，可继续砍，劈尽生成一块木材**；
2. **新树不再长在原木桩位置，而是在附近随机位置，按原曲线从小到大生长**。

## 1. 设计

### 1.1 树桩＝独立采集目标

| 项 | 规则 |
| --- | --- |
| 生命上限 | `ProductionTreeHealth::StumpMaxHealth` ＝ 同树立满生命 × **0.5**（含树种/尺寸系数；出厂斧 A 树桩约 2 挥、D 树桩 2–3 挥） |
| 生命存储 | 比例存 `FColdSteelTreeGrowth::StumpHealthRatio`（与树同样的"存比例不存绝对值"原则，调参不废旧档） |
| 目标识别 | 采集子系统随树桩渲染同一节拍重建**隐形碰撞盒**（复用 TrunkCollisionMesh＝100cm 立方，0.5 倍缩放落地，BlockAll），组件打 `HarvestStump` 标签；`ResolveProductionResource` 据此解析成 `FProductionResource{bStump=true}`（按盒位 ≤5cm 匹配，与树干盒同一套位置反查） |
| 结算 | `CommitStumpStrike`：扣桩生命；劈尽那一挥在桩边散落 **1 块木材**（`Rewards={wood:1}`，绕桩 ±65cm、±40° 朝向），记录 `bStumpCleared=true`，桩渲染与碰撞随脏标记消失 |
| 不受幼树门禁 | 桩任何时候都能劈（`CommitHarvestStrike` 的"生长中不可砍"门禁对 `bStump` 豁免） |
| 提示栏 | 瞄准桩显示"树桩 · 生命 N/M · 还需 N 挥"，读桩自己的比例 |
| 特效音效 | 劈尽＝木屑 Burst＋开裂声（复用 S_TreeCrack），无倒树 |

### 1.2 幼树偏移再生

- 砍倒瞬间 `RegisterTreeGrowth`（两处创建点统一）：
  - **桩留在被砍那棵树当时站的位置**（旧记录的 `SaplingOffset` → 新记录 `StumpOffset`；首伐＝候选点基点）；
  - **下一棵幼树在基点附近随机偏移**（半径 2.8–6.5 m，随机流按 `CandidateId+Generation` 播种）；最多重掷 5 次避河岸带（Bank>0.02）、陡坡（法线 Z<0.87）与世界边缘，都不行用最后一次——宁可位置差一点也不叠在桩上；
  - `Generation` 累计代数，作偏移随机流种子，同一候选点每次再生位置不同。
- 生长节奏不变：休眠 1 天 → 6 天成熟（`TreeDormantDays/TreeMatureDays`），缩放曲线 4%→18%→55%→100% 原样。
- **树桩不再自动缩没**：`TreeStumpScale` 退役旧"长回来时缩掉"曲线，改为 `未劈=1 / 已劈=0`——桩一直留着等玩家劈。
- 幼树扎根高度按偏移处当地地形取（`Height(X,Y)-10`），缩放仍绕根。
- 成熟后再砍：桩出现在偏移处的树位，幼树再换一处随机位——林子随砍伐缓慢"游走"。

### 1.3 边界与简化（如实记录）

- **每个候选点同一时间只有一个桩**：上一代没劈的桩在新一代被砍倒时被新桩替换（生长记录按候选点整体覆盖）。玩家想拿桩材就别攒着。
- 幼树偏移点不做树间距校验（可能贴邻树，纯视觉，概率低）。
- 旧档兼容：老记录无偏移字段 → 默认 0 ＝ 原地再生（表现与升级前一致）；老档已存在的桩（旧曲线会在 ~2 天缩掉的那些）改为常驻待劈。

## 2. 改动清单

| 文件 | 改动 |
| --- | --- |
| `UI/ColdSteelInventoryTypes.h` | `FColdSteelTreeGrowth` 追加 `Generation/SaplingOffset/StumpOffset/StumpHealthRatio/bStumpCleared`（只追加不前插） |
| `Production/ProductionResource.h` | `bStump` 标志 |
| `Production/ProductionTreeHealth.{h,cpp}` | `StumpMaxHealth`（口径唯一入口） |
| `UI/ColdSteelStatusModel.h` | 声明 `TreeSaplingOffset/TreeStumpOffset/StumpHealthRatio/CommitStumpStrike` |
| `UI/ColdSteelTreeGrowth.cpp` | `TreeStumpScale`→常驻 1/0；三个新访问器 |
| `UI/ColdSteelProductionTools.cpp` | 门禁豁免、桩分流、`RegisterTreeGrowth`（偏移+验证重掷）、`CommitStumpStrike` |
| `UI/ColdSteelProductionDrops.cpp` | 桩掉落布局（无倒树轴向，绕桩散落） |
| `WorldGeneration/TemperateHillsProduction.cpp` | `ResolveProductionResource` 树桩分支；`GetHarvestedStumps/GetRegrowingTrees` 偏移（枚举 ±1 格、入盒/扎根用偏移位）；`CompleteProductionHarvest` 树桩早退分支 |
| `Production/ProductionHarvestSubsystem.{h,cpp}` | `StumpTrunks` 碰撞组件＋`UpdateStumpTrunks`（与桩渲染同表同节拍）；`InvalidateStumps`；Deinitialize 清理 |
| `Production/ProductionToolComponent.cpp` | 桩不预载倒树网格；瞄准提示读桩生命比例 |

## 3. 性能

- 零新增 Actor/Tick/射线：桩碰撞与桩渲染共用已有的 1 s 刷新与同一份表（≤64 个矮盒，Clear+Add 实例化批量）；解析与结算都是挥砍时一次。
- 偏移在砍倒瞬间一次性算出并存档，之后纯读。

## 4. 验证状态（如实声明）

- C++：随本轮 Game+Editor 构建编译（`Saved/BuildEditor/build-stump-20260928-*.log`）。
- 运行时表现**未实测**（用户规则）。实测看点：
  - 砍倒后桩上出现可瞄准的"树桩 · 生命 N/M"，2 挥左右劈开掉 1 块木材、桩与碰撞消失；
  - 同时候选点附近 3–6.5 m 处出现幼苗，按原曲线 6 天长回；
  - 幼苗期劈树仍被拒（"正在生长"），但劈桩不受影响；
  - 再砍倒成熟树：新桩在新树位，幼树再随机换位。

## 5. 调参入口

- 桩生命占比：`ProductionTreeHealth.cpp` `StumpMaxHealth` 的 `.5`；
- 偏移半径/重掷次数：`ColdSteelProductionTools.cpp` `RegisterTreeGrowth`（280–650、5 次）；
- 生长节奏：`DA_TemperateHills` 的 `TreeDormantDays/TreeMatureDays`（未动）。
