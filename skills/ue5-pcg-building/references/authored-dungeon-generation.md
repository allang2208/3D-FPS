# 保留设计语义的随机地牢

用于 FPSGAME 已认可样板的房间扩展、随机目录、侧室、岔路和终点接入。原生入口是 `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator`，生产关卡为 `/Game/GameMaps/L_Dungeon_Randomized`。不要误用仍有存档兼容引用的旧 `Source/FPSGAME/Dungeon/` 生成器。

## 配方与空间关系

- 随机装配的单位是完整作者房间：保留轮廓、层高、低顶侧间、管道、隔栅和遗迹侧穴。房间只做刚体平移和旋转；可变长度只用于指定的直线连接段。曾被退回的 `DungeonGenerationV1` 方盒房配方不是风格模板，废案在 `trash/dungeon-random-boss-retired-20260923`。
- 固定起点包含标准通道、工作间、仓库柜和神像。之后每组抽取 3–5 间普通房，再接联通通道。普通房池与 Junction、Transit、Threshold、RouteElbow、Treasure、Boss 终点分别配置，不能用总模块数冒充战斗房数。
- 2026-09-23 的普通房 ID 为 Distribution、Drainage、ShoredBreach、VentilationLoop、FreightTransfer；扩展注册位于 `DungeonRoutes20260922/Config/room-extensions.json`。宝箱侧室是每个合格普通房 10% 的放置尝试，空间不足可以放弃，不等于每轮固定 10% 出现。
- 装饰使用独立种子流，不能因增减装饰而改变房间、侧室或 Boss 路线。墙面剥落继承已认可通道几何、UV 和材质，排除被退回的矩形整片和三角碎片设计。

## 门洞与避让

房间扩大时，同时更新真实墙体开口、门框、端口元数据、带侧门墙体变体和接头。该项目的随机房接口为 300×280 cm；固定样板入口保留 132×238 cm，以侧壁、顶和地面封闭的过渡段衔接。只改端口数字会出现门框外漏空。

占位使用真实 `cells`，特别是 L 形房间和侧穴，不能仅按宽松总包围盒判断。先预留侧室与入口通道，再替换带门墙体；放不下时保留完整墙。Boss 先预留大厅、汇流室和最终接头，再对三条支线做直角路线搜索；直段及转角均计入占位。搜索失败回溯或取消方案，不穿过墙体强行接通。

## 目录与装配提交

新增模块同时遵守 [性能开发约束](../../ue5-performance-packaging/references/fpsgame-performance-development.md)：刚体几何制作与重导策略一致；局部灯既覆盖生成房间，也覆盖固定起始区。复用已有装配分片与房间灯调度，保留近景、碰撞、导航准备顺序和重新生成时的状态恢复。

1. `catalog.modules` 是唯一模块列表。扩展过程中替换它以后，不能继续向旧的 `modules` 局部列表追加。更新全部普通房 ID，并排除重复或缺失 ID。
2. 基础房、宝箱、新房扩展之后，最后应用 `DungeonRouteRepairs20260922/Scripts/extend_catalog.py`。否则后运行的旧安装器可能恢复旧门洞、丢失侧门或禁用 Boss。增量安装保留地图现有扩展与宝箱配置。
3. 装配先预载资产，暂存新 Actor、布局描述和清单，完成后再替换旧实例。失败只清理本批暂存物并恢复目录及资源引用。安装器只有看到 `DungeonAssembly.Ready` 且没有 `DungeonAssembly.Failed` 才保存目标地图。
4. 所有静态网格、材质、动画和 `_C` 蓝图类进入资源清单及关卡硬引用。类路径使用类加载接口，不能一律当普通 asset 加载。
5. 编辑器制作可保存的导航 Brush 模板，运行时按布局移动、缩放并通知动态导航；不能在游戏中依赖编辑器构建 Brush。导航准备结束后释放玩家、启动粘液伤害和 Boss 入场控制。

## 接入入口与证据

依赖顺序见项目 `Docs/Gameplay/dungeon-random-boss-publication-20260923.md`。修复制作入口为 `prepare.py` → Blender `author.py` → 桥内 `import_assets.py` → 必要原生构建与加载 → 桥内 `install.py`。已有完整资产时只运行所需安装阶段，已归档的一次性源码补丁和恢复脚本不能再次执行。

Boss 房生成与敌人生成分开说明。终点配置启用不代表存在战斗触发；实际接入见 [Boss 遭遇生命周期](../../ue5-monster-workflow/references/dungeon-boss-encounter.md)。2026-09-23 已有原生构建、导入和地图保存记录；这些不是多种子、寻路、战斗或视觉测试。默认交由用户测试，不自动启动 PIE 或渲染。
