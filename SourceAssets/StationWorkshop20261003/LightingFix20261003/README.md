# 办公室顶灯关闭投影

按用户截图要求，`StationWorkshop.MaintenanceCeiling` 的 `cast_shadows` 改为 `false`，保留原亮度、颜色、范围及主灯角色。调度侧顶灯和工作台灯原来已无投影。

同步目标为正式随机地牢生成器目录和车站测试地图的 `StationWorkshop_Light_0` Actor。实际地图保存状态以 `Receipts/install.json` 为准；原地图和目录备份在 `Backup`。

主点位作者、V3/V4 当前工作间配置及 V4 修正入口均保留该灯的无投影设置。没有模型、材质或原生代码变更，无需导入和编译。未运行游戏、测试、截图或渲染，由用户继续试玩。
