# 保留设计语义的随机地牢

用于 FPSGAME 已认可样板的房间扩展、随机目录、侧室、岔路和终点接入。原生入口是 `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator`，生产关卡为 `/Game/GameMaps/L_Dungeon_Randomized`。不要误用仍有存档兼容引用的旧 `Source/FPSGAME/Dungeon/` 生成器。

## 配方与空间关系

- 随机装配的单位是完整作者房间：保留轮廓、层高、低顶侧间、管道、隔栅和遗迹侧穴。房间只做刚体平移和旋转；可变长度只用于指定的直线连接段。曾被退回的 `DungeonGenerationV1` 方盒房配方不是风格模板，废案在 `trash/dungeon-random-boss-retired-20260923`。
- 固定起点包含标准通道、工作间、仓库柜和神像。之后每组抽取 3–5 间普通房，再接联通通道。普通房池与 Junction、Transit、Threshold、RouteElbow、Treasure、Boss 终点分别配置，不能用总模块数冒充战斗房数。
- 2026-09-23 的普通房 ID 为 Distribution、Drainage、ShoredBreach、VentilationLoop、FreightTransfer；扩展注册位于 `DungeonRoutes20260922/Config/room-extensions.json`。宝箱侧室是每个合格普通房 10% 的放置尝试，空间不足可以放弃，不等于每轮固定 10% 出现。
- 装饰使用独立种子流，不能因增减装饰而改变房间、侧室或 Boss 路线。墙面剥落继承已认可通道几何、UV 和材质，排除被退回的矩形整片和三角碎片设计。

## 门洞与避让

2026-09-24 的扩展继续保留房间刚体尺寸，通过形状变体、朝向和短直段/转角适配错位接口；仅指定直线连接段允许长度变化。地下 Boss 路由使用三维 cells 占位与预留出口，不再用纯 XY 相交拒绝上下层。规划预算不足时调整终点候选和支线搜索顺序，失败保留旧场景，不能退回穿墙直连。详见工程 `dungeon-short-links-failure-fix-20260924.md` 与 `dungeon-underground-boss-routing-v2-20260923.md`。

房间扩大时，同时更新真实墙体开口、门框、端口元数据、带侧门墙体变体和接头。该项目的随机房接口为 300×280 cm；固定样板入口保留 132×238 cm，以侧壁、顶和地面封闭的过渡段衔接。只改端口数字会出现门框外漏空。

占位使用真实 `cells`，特别是 L 形房间和侧穴，不能仅按宽松总包围盒判断。先预留侧室与入口通道，再替换带门墙体；放不下时保留完整墙。地下 Boss 路由先完成中路，再以中路出口定位完整楼梯、地下汇流和 Boss 终点，随后闭合两条外路；直段及转角均计入占位。搜索失败回溯或取消方案，不穿过墙体强行接通。

## 目录与装配提交

新增模块同时遵守 [性能开发约束](../../ue5-performance-packaging/references/fpsgame-performance-development.md)：刚体几何制作与重导策略一致；局部灯既覆盖生成房间，也覆盖固定起始区。复用已有装配分片与房间灯调度，保留近景、碰撞、导航准备顺序和重新生成时的状态恢复。

1. `catalog.modules` 是唯一模块列表。扩展过程中替换它以后，不能继续向旧的 `modules` 局部列表追加。更新全部普通房 ID，并排除重复或缺失 ID。
2. 基础房、宝箱、新房扩展之后，最后应用 `DungeonRouteRepairs20260922/Scripts/extend_catalog.py`。否则后运行的旧安装器可能恢复旧门洞、丢失侧门或禁用 Boss。增量安装保留地图现有扩展与宝箱配置。
3. 装配先预载资产，暂存新 Actor、布局描述和清单，完成后再替换旧实例。失败只清理本批暂存物并恢复目录及资源引用。安装器只有看到 `DungeonAssembly.Ready` 且没有 `DungeonAssembly.Failed` 才保存目标地图。
4. 所有静态网格、材质、动画和 `_C` 蓝图类进入资源清单及关卡硬引用。类路径使用类加载接口，不能一律当普通 asset 加载。
5. 编辑器制作可保存的导航 Brush 模板，运行时按布局移动、缩放并通知动态导航；不能在游戏中依赖编辑器构建 Brush。导航准备结束后释放玩家、启动粘液伤害和 Boss 入场控制。

## 接入入口与证据

2026-09-26 的 V4 首批实现见项目 `Docs/Gameplay/dungeon-topology-v4-implementation-20260926.md`：保留三路地下终点骨架，新增预先确定的房数分配、通道偏好和可选普通房回路。回路使用完整侧门墙体及短连接，真实放不下时保留封墙；不能把目标 1–2 条称为保证生成。清单 V4 输出真实门洞/cells/入口，玩法邻接沿完整 connector 链处理；等级与战利品读取排除额外回路的 `progression_depth`。地下模式不得回退到同层终点并继续标记 compact。任意任务图与共享房壳多主门配方仍未完成。

依赖顺序见项目 `Docs/Gameplay/dungeon-random-boss-publication-20260923.md`。修复制作入口为 `prepare.py` → Blender `author.py` → 桥内 `import_assets.py` → 必要原生构建与加载 → 桥内 `install.py`。已有完整资产时只运行所需安装阶段，已归档的一次性源码补丁和恢复脚本不能再次执行。

Boss 房生成与敌人生成分开说明。终点配置启用不代表存在战斗触发；实际接入见 [Boss 遭遇生命周期](../../ue5-monster-workflow/references/dungeon-boss-encounter.md)。2026-09-23 已有原生构建、导入和地图保存记录；这些不是多种子、寻路、战斗或视觉测试。默认交由用户测试，不自动启动 PIE 或渲染。

## 2026-09-26 V4 后续接入（清单 V5）

任务图和多主门共享配方已接入源码，细节及构建/落盘回执见 `Docs/Gameplay/dungeon-v4-complete-20260926.md`。不再把上一段的“仍未完成”当作当前源码状态。

- `AuthoredDungeonMission.inl` 在几何放置前选择同点三岔、先左后右、先右后左规则，必需边与物理端口图对应；可选回路记录是否实际落位。仍保留三个地下入口和 Boss 战后奖励门。任意任务图不是当前支持范围。
- `room_recipe_library` 由 `AuthoredDungeonCatalog` 展开；两个通风外壳 × 三个兼容内部布置共享网格。多门普通房通过 `port_pairs` 明确选进出门，未使用门必须有 `closed_port_parts` 实体封口。不能恢复普通房统一 `1-Entry` 的假设。
- `walk_mask` 过滤遭遇候选，`encounter_anchors` 与现有锚点流程相接。硬引用需包含闭门构件；目录重建最后叠加 `DungeonComposition20260926`，保留现有资产和材质。
- 逻辑节点身份、设计推进阶段、角色、实际连接件缩放和选中配方进入布局清单；档案保留生成器版本和完整清单。原先每次进入生成新局的生命周期不变，不声称新增断点续局。
- 每条连接预算和全局总量预算同时保留。`route_span_estimate_cm` 是按房壳和作者标定楼梯估算的路线尺度，不是导航实测长度。
- 精英职责读取任务角色；宝箱领取记录与全部物品同事务保存，背包满转保存的地面掉落。风险清房奖励只发给有实际击杀的房间，并与清房状态一并提交。
- 资产目录安装只保存生成器配置和依赖；用户未要求测试时不为 `DungeonAssembly.Ready` 启动生成器、PIE、种子遍历或截图。必要构建及实际保存回执不等于运行验收。


## 2026-09-27 废弃设施功能布置

- 排水、通风和货运房继续复用既有房壳。新增层位于 `SourceAssets/DungeonFacilityScenes20260927`，各家族三种设备配方、每种三种环境状态；这是组合布置，不是二十七间新房。
- `AuthoredDungeonRoomScenes` 在路线规划结束后使用独立种子选择 `scene_recipes` 与状态，按家族避开连续重复；布局节点保留 `scene_recipe_id`、`scene_state_id`。不要把装饰抽签放进路线随机流。
- 摆放使用作者指定设备位及 `scene_keep_clear`，保留门口、桥面和可选侧门。每房最多增加三个组合网格，零散物件上限 8、物件簇上限 2、不增加灯光；大设备 UCX，小杂物无碰撞、无导航。
- 目录重建在 Composition 层后保留 FacilityScenes 扩展及网格硬引用。后台入口为本批 `Scripts/background_install.py`，只导入和保存配置，不运行布局预览。commandlet 中直接读 BodySetup 碰撞数组，不能依赖可能为空的 StaticMeshEditorSubsystem。
- 已有本轮 Editor 基础 DLL 构建、九款网格和地图生成器保存回执；无游戏、视觉或性能测试。具体记录见工程 `Docs/Gameplay/dungeon-facility-scenes-20260927.md`。走动卡顿尚未完成帧采样归因，不把成本上限当作性能实测。

## 规划失败与构造预算的复用经验（2026-09-27）

- 连接预算覆盖两端预留套筒和整个连接链；不能只检查求解器新生成的段。路线尺度沿实际入口到终点的模块链统计，排除可选回路重复计费，仍与 NavMesh 实测长度分开。
- 先放置可达中路，再以其出口定位地下终点；允许中间房在既有 cells、lane 和门位约束内回折。增加搜索次数不能修复被错误排除的空间方案。
- 新设备通过组合配方加入房间时，使用独立随机流与明确占位，避免重导出每份整房。大型构件的 UCX 与小装饰无碰撞分别表达；commandlet 直接读取 BodySetup 聚合形体，凸包不能漏计为“没有碰撞”。
- 神像朝向用每个网格的正面轴与房间出口方向求旋转；破洞截面沿已有真实墙厚制作，不能只贴薄片。现行房间制作见工程 `Docs/Gameplay/dungeon-shrine-room-v2-20260927.md`。
