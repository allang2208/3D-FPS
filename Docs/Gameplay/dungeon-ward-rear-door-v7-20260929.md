# 病区后通道门框 V7

用户补充截图：后通道门洞顶部及侧边仍有混凝土和金属交替显示。V6 修改了观察窗以及后门设备横槽，但固定门框仍沿用三个盒体，且内侧面与混凝土洞口封口面共面。

本轮将固定门洞的结构开口向两侧及上方各退让 5 mm，封口面藏进门框实体内；金属门框改为单个连续 U 形截面，去掉柱顶与横梁接触处的重复端面。可见通行宽高、门框位置、材质及玻璃门交互均保留。共用同一固定门洞生成函数的入口采用同一修正。

仅重新导出 `SM_Ward_Walls`（7,344 三角面）和 `SM_Ward_Frames`（39,444 三角面），路径仍为 `/Game/Dungeons/IsolationWard20260929/Meshes/`。已保存的样板地图继续引用原资源路径，无需另存地图或更换 Actor。

- 可编辑几何：`SourceAssets/DungeonIsolationWard20260929/Authored/WardRearDoorFixV7.blend`。
- 作者：同目录 `Scripts/author_ward.py`，`WARD_EXPORT_KINDS=Walls,Frames`。
- 重导及保存：`Scripts/apply_rear_door_v7.py`，完成回执为 `Receipts/rear-door-v7.json`；实际接入状态见 `Receipts/delivery.json`。
- 修改前两份 UE 资产、作者、配置和清单保存在 `SourceBackup/BeforeRearDoorV7/`。

本轮无 C++ 改动，不需要 DLL 构建。未启动游戏、PIE 或渲染复测；用户自行确认实际画面。

两份 UE 资产已通过后台 commandlet 实际重导保存，退出码 0；`Receipts/install-v7-commandlet.log` 记录 `WARD_REAR_DOOR_V7_SAVED`。编辑器关闭后转用后台导入，没有打开或重启编辑器；没有改写地图，原地图的同路径资源引用直接取得修正模型。
