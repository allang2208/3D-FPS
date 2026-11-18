# 丘陵村庄外围石墙：残破与修复两种状态

2026-11-17。按用户要求，参考当前教堂院墙，在山顶村庄外围增加石墙。默认残破，后续通过任务修复。本批制作墙体、放置、碰撞及持久／联机状态入口；不新增任务目标、材料消耗、NPC 对话或奖励。

## 造型与范围

- 沿用教堂院墙的分层毛石、薄片石和压顶石构造，以 `M_ChapelYardField`、`M_ChapelYardSlate`、`M_ChapelYardCap` 为源制作外围墙专用副本，砂浆仍引用原材质。仅石块根部约 4–8 cm 加入不规则、低强度的现场泥土混合，保留石材法线和上部原材质；不修改教堂或武器资产。
- 完整墙段长 300 cm、厚约 62 cm、地上高约 166 cm，完整墙柱高约 198 cm。地下埋入约 35 cm，基准位于真实地面。两个完整墙段变体减少重复。
- 残破版有四种独立断墙轮廓，墙顶从约 23–145 cm 不等，含倒塌缺口与两种低矮墙脚碎石。断口核心由不规则石块构成，取消外露的阶梯状砂浆盒。墙根有半埋的小石屑，倒塌大块压低并混入大小碎片。缺口处没有整块隐藏碰撞；碎石不阻塞通行。墙柱也有单独破损版本。
- 外围按村庄局部轴布置，位于平坦预留区内侧 5 m；当前 V3 对应约 130×100 m 的八边轮廓，四角各削去 6 m。保留原房屋／教堂院墙和内部道路。
- 西侧进村路中心 `y=0` 留出 10 m 墙端间距；东侧 `y=500 cm` 留出 8 m，两边有石柱，实际净宽扣除柱宽。没有新增封闭门扇。
- 原有种子确定墙段与破口组合；修复前后使用同一组墙体位置。黄色丘陵、雨林范围、地形、神像与夜袭规则不改。
- 仅在 V3 山顶村庄生成这圈墙。V1／V2 的旧尺寸村庄不强行套入大型外围墙。

## 资产与制作

资产目录：`/Game/WorldGeneration/TemperateHills/VillagePerimeter`。

| 角色 | 资产后缀 | LOD0 三角形 | 简单碰撞 |
| --- | --- | ---: | --- |
| 完整墙段 | RepairedA / RepairedB | 各 9040 | 每段 1 个盒 |
| 残破墙段 | RuinedA / RuinedB / RuinedC / RuinedD | 9136 / 8080 / 5704 / 5792 | 随实际断面，6 / 6 / 4 / 4 个盒 |
| 墙柱 | PierRepaired / PierRuined | 2016 / 1752 | 各 1 个盒 |
| 碎石 | RubbleA / RubbleB | 各 1864 | 不阻塞 |

前缀统一为 `SM_VillageWall`。模块使用 Nanite、完整光追回退几何、明确材质分区及每 UV 100 cm 的石材密度。原生按款式分组为 ISM，不为每块石头创建 Actor，也不新增逐墙 Tick。墙体拒绝贴花，避免地面投影覆盖石材。

作者入口：`Tools/WorldGeneration/VillagePerimeter/wall_geometry.py`。可编辑网格源与几何制作回执位于 `SourceAssets/HillsVillagePerimeter20261117/wall-mesh-source.json`、`geometry-production.json`。

后台导入入口：`Tools/WorldGeneration/VillagePerimeter/Import-Walls.ps1`，调用 `import_walls.py`，仅保存该目录下的十个网格及 `Materials/Receivers` 中的专用材质。`ground_transition.py` 复用现有村庄地表 RVT 构建器，短距离混合只发生在外围墙材质本身，不向其他物体投射贴图。实际保存回执为同批 `asset-production.json`、`import-process.json`。烹饪目录已登记，石材作为网格依赖随资产收集。

## 任务修复接口与状态合同

- 真实状态拥有者：`ATemperateHillsWorld`。稳定存档字段 `UTemperateHillsSave::bVillageWallRepaired`，默认 `false`，旧档缺失字段也为残破。
- 世界存档 schema 增至 V5，不改变 GeneratorVersion、种子、WorldId、原地形编辑记录。旧 V1–V4 档仍可读取；仅后续创建／保存或修复时写入 V5，本次制作不重写当前正式存档。
- 状态范围：当前丘陵 WorldId，全队共享并跨退出／重新进入保留；重新生成新的 WorldId 时回到残破。
- 后续修复任务建议稳定 ID 为 `hills.village.restore_perimeter`，实例使用该 WorldId。具体目标、接取、消耗和奖励尚未制作，不向任务栏发布虚构进度。
- 实际目标完成后，由服务器任务拥有者调用 `CompleteVillageWallRepair(FText& FailureReason)`。返回成功后，任务才能提交完成反馈／奖励；失败则保留任务待交付，并显示原因。
- 接口拒绝客机直接写入。完成墙体位置有玩家或动物占用时返回失败，避免补墙把角色卡入碰撞；让开后可再次提交。
- 先保存本世界修复状态，再更新墙体／碰撞并 `ForceNetUpdate`。重复调用已完成的修复返回成功，不再次落盘或创建第二圈墙。
- `bVillageWallRepaired` 通过现有始终相关的丘陵 Actor 复制，`OnRep_VillageWall` 只更新表现和碰撞，不发奖励或写存档。进度先于村庄加载到达时，装配读取已复制状态；迟加入也读取同一状态。
- `IsVillageWallRepaired()` 为任务和 UI 的只读状态入口。未来 HUD 接入遵循 `TASK-WORKFLOW.md` 的真实任务来源流程；这个接口不代表整条修复任务已经完成。

原生实现集中在 `Source/FPSGAME/WorldGeneration/TemperateVillagePerimeter.cpp`；资源进入原教堂异步预加载批次，沿用其持续持有的资源句柄；不在修复回调中同步加载资产。

## 交付范围

初次制作完成了 Editor 与 Game 的 Win64 Development 构建和后台资产落盘，当时未运行游戏。随后用户明确要求检查布局、细节及接地，追加以下限定范围的实景检查；任务完整流程、联机和怪物寻路不在本次检查范围。

## 2026-11-17 实景检查与修正

- 在当前种子 `1518277816` 的隔离存档副本中检查残破与修复状态。修复状态仅在检查进程里切换，正式存档仍默认残破。
- 首轮截图及数据：`SourceAssets/HillsVillagePerimeterCheck20261117/Before`。两种状态共 870 个墙体接地点采样，根部基准与实际动态地面误差为 0 cm；两个入口均未被围墙碰撞阻挡。固定全景、断墙近景、贴地近景、门口和转角机位。
- 首轮实际仅生成 RuinedA / RubbleA / RepairedA，原因是 `RandHelper(MAX_int32)` 通过浮点数缩放，抹掉了款式选择用的低位。改用整数随机数的高 24 位，恢复四种断墙、两种完整墙和两种碎石的种子选择；墙线、门口与缺口位置保持不变。
- 根据近景修正外露的方形砂浆核心、过于孤立直立的碎石，以及过硬的石土交界。既有墙脚已埋入地面，未盲目再次下沉整圈墙体。
- 修正后实景回执：`SourceAssets/HillsVillagePerimeterCheck20261117/After/result.json`。残破版 198 个实例、7 个网格款式；修复版 157 个实例、3 个款式。分别采样 594 / 471 个实际动态地面接点，总计 1065 点，其中 195 点属于倒塌碎石。所有点均命中实际地面，放置基准与地面高度差为 0 cm；实体墙最低网格底部埋深至少 36.63 cm，碎石组至少 11.73 cm。这些是放置基准及网格边界采样，结合近景判断接地，不等同于逐个顶点测试。
- 两种状态的东西入口胶囊扫描均未命中围墙碰撞；实际全景、两侧门口和转角截图确认连续墙线与预留出入口关系。场景检查只针对当前种子，没有据此宣称所有种子、联机或怪物寻路通过。
- 修正后保存了 12 张 1920×1080 实际运行截图，`ruined-*` / `repaired-*` 分别为默认残破及修复款，包含 overview / wall-detail / ground-contact / west-gate / east-gate / corner。两款使用同一组机位和相同白天天气；首轮已有的五组机位保持一致，复查追加东入口。全景用于围墙布局，远景生态仍受运行时流式加载范围影响，不作为新一轮雨林验收。
- 编译回执：`SourceAssets/HillsVillagePerimeterCheck20261117-Fix/FPSGAMEEditor-build.json`、`FPSGAME-build.json`，均退出 0。后台导入十个网格和三种专用石材完成，`SourceAssets/HillsVillagePerimeter20261117/import-process.json` 退出 0。首个材质导入尝试受原材质属性辅助接口目录限制而中止，未保存网格；砂浆继续使用原材质，专用接地仅应用于三种石材，重试完成。失败日志保留在 `HillsVillagePerimeterCheck20261117/ImportAttempt1`。
- 两次隔离实景进程都正常退出 0，`Before/runtime-process.json` 与 `After/runtime-process.json` 均记录正式丘陵存档 SHA256 未改变。正式世界仍是原种子、默认残破状态，没有提交任务修复状态。
