# 主泵房终点与手脑首领接入

本批延续已认可的 30×26 m Boss 主泵房源模型，不改房间设计。用户于本轮选择复用手脑首领，完成入场与战斗接入。模型来自 `DungeonBossHall20260922`，房间池仍为五种普通房；Boss 仅作为唯一终点，由三条支路进入汇聚前厅，再经连接通道抵达。

## 入场规则

- 手脑使用现有 `/Game/Monsters/HandBrain/BP_HandBrain`，保留生命、攻击、动作、受击、布娃娃与击杀奖励；仅扩大这个实例的感知与活动范围以覆盖大厅。
- 地牢新布局装配完毕、导航准备完成后启用入场控制。旧预览中的控制器不自动激活。
- 玩家进入门内至少 1.8 m 后，按 `boss_spawn` 锚点投射到手脑规格的导航网格；附近有阻挡、资源缺失或导航尚不可用时不封门，离开再进入可以重试。
- 成功生成唯一手脑后，钢栅入口下降并封锁。门控与怪物 AI 分工独立，行为决策仍走现有 MonsterAIController 与 Behavior Tree。
- 首领生命归零即解除封锁；沿用手脑自身的一次击杀奖励，不额外重复发放。尸体按原有时间回收。本次地牢不再次刷新该首领。
- 玩家死亡、传送离开大厅或首领异常消失时，取消本次战斗并开放入口；离场后可以重新进入挑战。重新生成地牢或卸载关卡会清理本控制器拥有的首领。

## 文件和接入

- `Source/FPSGAME/Dungeons/DungeonBossEncounter.h/.cpp`：独立入场、封门和战斗生命周期。
- `AuthoredDungeonGenerator.cpp`：按 Boss 模块配方创建控制器，并在完成导航后激活。
- `DungeonRouteRepairs20260922/Scripts/extend_catalog.py`：导入完整后启用唯一 Boss 终点及首领配方；所有安装器保留其类与材质硬引用。
- Boss 材质导入脚本的管道腐蚀遮罩改用 Saturate 节点，修复 UE Python 不存在 `Clamp.min_default` 属性导致的导入中断。

先完成必要原生构建并加载新 DLL，再通过项目桥执行素材导入及 `Scripts/install.py`。首轮导入的前九份材质已完成；一次性恢复脚本从两份管道材质恢复并导入 23 个网格后，已移至 `trash/dungeon-random-boss-retired-20260923`；后续全量素材导入使用 `Scripts/import_boss.py`。最终地图接入结果记录在 `Receipts/install.json`；没有该成功回执时不能宣称地图接入完成。

本轮不启动 PIE、测试、多种子采样、截图或渲染。编译和资产保存属于开发接入，不代表寻路、战斗、视觉或性能验证，交由用户测试。

## 本次实际接入结果

常规 Editor 构建完成，最后一次必要编译结果见 `Receipts/build-editor-02.log`。23 组 Boss 网格已导入，素材恢复调用见 `Receipts/import-04.txt`。随机地图 `/Game/GameMaps/L_Dungeon_Randomized` 已保存，`boss_terminal_enabled=true`，当前固定编辑器种子 92247 的装配结果包含唯一 Boss 房；三条支线汇入终点前厅，首领类为 `BP_HandBrain`。地图装配回执见 `Receipts/install.json` 与 `Receipts/install-01.txt`。共 299 个模块（包括汇流直线连接段与转角），不是 299 间战斗房。未运行游戏或战斗测试。
