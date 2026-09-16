# 范围拾取、体素块物品与提示栏（2026-09-16）

用户要求：① 把残骸变成体素块（若没有该物品就按非枪械物品工作流新增，共 3 种）；② 新增 Z 键范围拾取，一键拾取范围内所有物品（含体素块、装备等）；③ 背包满时在屏幕上方"升级提示"的位置显示"背包已满"，并把该位置定义为后续播报各类提示的**提示栏**。

## 体素块物品（3 种）

按 [非枪械物品工作流](../../skills/ue5-item-asset-workflow/SKILL.md) 接入物品目录 `Content/ColdSteelData/items.json`（本次没有新建模型与图标文件，理由见下）：

| 定义 ID | 名称 | 类型 | 堆叠 | 图标 |
| --- | --- | --- | --- | --- |
| `voxel_block_wood` | 木材体素块 | 建材 | 999 | `Icons/wood.png`（工程既有写实材质图标） |
| `voxel_block_stone` | 石块体素块 | 建材 | 999 | `Icons/stone.png` |
| `voxel_block_marble` | 大理石体素块 | 建材 | 999 | `Icons/marble.png` |

- **模型**：体素块的"模型"就是建造用的 20 cm 体素方块本身，因此拾取物直接取活动调色板 `DA_VoxelBuildPalette` 里该材质的 `ExampleMesh` 与 `Surface`（`AColdSteelPickup::BuildVoxelBlock`），地面上的方块和放下去的方块完全一致；缺省回落到 `SM_Voxel20_Stone`。
- **图标**：复用工程里既有的写实材质图标（wood/stone/marble）；没有为方块姿态单独生成新图。需要"方块造型图标"时再按图标工作流补。
- 物品可堆叠 999，在背包/仓库里按普通材料展示，可拖放、拆分、存放。

## 残骸 → 体素块

- 残骸（倒塌或失败放置产生）**落地静止 2 秒**后由 `AVoxelBuildWorld::TickFragments` 回收：按材料把格数汇总成方块物品（一次事务写入存档），调用 `UColdSteelStatusModel::GrantWorldBlocks` 生成世界掉落（`Place=2`，普通掉落物，可由 `RefreshDrops` 生成拾取 Actor），随后销毁残骸 Actor 并标记存档。
- 因此残骸不再是永久物理垃圾：拆掉/塌掉的墙会变成地上的方块堆，可以捡回来继续用。
- 边界：仅单机世界；材料目录缺失、地面物品已达 10000 上限或保存失败时保留残骸并给出提示，不静默丢失。

## Z 键范围拾取

| 项 | 内容 |
| --- | --- |
| 入口 | `AFPSGAMEPlayerController::InputKey` → `Z`（Ctrl+Z 仍是建造撤销，构建中由建造组件先行消费） |
| 半径 | 控制台 `fps.Pickup.AreaRadiusCm`，默认 **500 cm** |
| 范围 | 当前地图中 `Place=2` 的全部地面掉落：体素块、装备、材料、消耗品等一视同仁 |
| 视线 | **不隔墙/隔层吸**：从玩家胸口朝物品画多段线，只有阻挡点不高于玩家脚下 **40 cm**（能迈过去）才算通过（2026-09-16 用户指定）；更高的墙、地板隔层、箱子都算阻挡 |
| 事务 | 一次 `Snapshot → Insert → CommitState`；放不下的物品**按原位置留在原地**（不会丢），并自动调用 `RefreshDrops` 同步拾取 Actor |
| 反馈 | 成功：`Message=已拾取 N 件物品`；空：`附近没有可拾取的物品`；有剩余：提示栏播报"背包已满 · 已拾取 N 件 · M 件留在地面" |

## 提示栏

- 复用既有升级提示：`FColdSteelProgressNotice`（Title/Detail/Icon/Duration）+ `UColdSteelProgressNotification`（屏幕上方，2.8 s 默认时长，现有淡入淡出与音效）。
- 新增通用入口 `UColdSteelStatusModel::PostNotice(Title, Detail, Icon, Duration)`；升级提示（角色/技能）继续走原有队列，二者共用同一队列与同一位置，先入先播。
- 第一个使用者：范围拾取在背包放不下时播报"背包已满"。后续新功能统一往这里推送提示，不再另起浮层。

第二个使用者：**结构预警**（见下）。凡是"一次性、需要立刻告诉玩家"的信息都走这里，面板内的常驻读数不占用提示栏。

## 拆除回收（2026-09-16 追加）

- 建筑模式**右键拆除体素**：先按材料统计本次要移除的格，编辑成功后调用 `GrantDismantledBlocks` —— **优先进背包**（`UColdSteelStatusModel::AddItem` 逐材料一次事务）；装不下的部分立刻变成脚下的方块掉落（`GrantWorldBlocks`），并在提示栏播报"背包已满 · N 块体素掉在脚下 · 按 Z 拾取"。编辑失败（重叠、存档拒绝等）不发放，绝不凭空产出物品。
- **右键拆除残骸**：静止的残骸改为"直接回收"——按材料把整块残骸的格数转成体素块（同样先进背包，溢出掉脚下），随后 `AVoxelBuildWorld::RemoveFragment` 移除记录与 Actor；仍在空中下落的残骸保持原来的撞碎逻辑。
- 残骸**自动回收**（落地静止 2 秒）仍走世界掉落（`GrantWorldBlocks` → 地上的方块，E/Z 拾取），与"主动拆除直接进包"区分开。

## 文件与交付

- 新增：`Source/FPSGAME/UI/ColdSteelPickupVoxelBlock.cpp`（体素块拾取物外观）、`Source/FPSGAME/UI/ColdSteelAreaPickup.cpp`（提示栏、范围拾取、残骸转方块）。
- 修改：`Content/ColdSteelData/items.json`（3 个新物品）、`ColdSteelPickup.h/.cpp`（接入体素块外观与质量）、`ColdSteelStatusModel.h`（3 个新接口）、`FPSGAMEPlayerController.cpp`（Z 键与控制台变量）。
- 本轮还改了建造侧：残骸不计活荷载与体素重量 1/4，见 [垂直建造排查](../../Building/voxel-vertical-build-diagnosis-20260916.md)。
- 必要构建：Editor Development（新增 UCLASS 成员与源文件，不能热补丁）。
- 未要求预览/检查/测试；由用户测试。
