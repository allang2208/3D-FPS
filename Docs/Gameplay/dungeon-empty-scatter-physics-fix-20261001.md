# 地牢装配阶段空病床组件的碰撞失败

2026-10-01 用户运行到 81% 时失败。现有 `Saved/Logs/FPSGAME.log` 的 14:19:50 UTC 报错对象为 `WardBedScatter_0.Beds`；此前已经完成规划并进入资产与交互件装配。本次故障发生在装配阶段，不能将其作为布局仍未找到的证据。

`WardRoomAssembly::Spawn` 配置病床散布器，但禁用自动 BeginPlay 散布，让它在房壳及门体碰撞就绪后才由 `Dungeon.WardFurniture` 任务填入实例。装配器会先处理新 Actor 的碰撞，此时 `Beds` 为零实例，网格也尚未通过 `GenerateFromSeed` 赋给组件。原判断要求所有启用碰撞的组件立即拥有物理状态，从而在填充之前报错并回滚。

修改位于 `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp`：

- 物理激活阶段跳过零实例 ISM；拥挤房间最终未放入家具也是合法零结果。
- 家具填充后将该 Actor 单独送回现有物理激活阶段，处理病床及新生成的家具组件，不重新扫描全地牢。
- 非空 ISM、普通墙地和坡道继续要求碰撞创建成功；异步创建尚未结束时等待后续切片，碰撞完成之前不提交场景。
- 保留每帧装配预算、失败回滚、导航就绪与玩家释放顺序，不通过关闭病床碰撞消除报错。

本次只修复装配生命周期，不改主题房顺序、错层规则、模型资产或刷怪配置。

后台构建 `FPSGAMEEditor Win64 Development` 已完成，UBT 返回 `Target is up to date`、`Result: Succeeded`，日志为 `Saved/BuildEditor/dungeon-empty-scatter-20261001.log`。当前源码对应的目标已是最新，无需重复编译。未启动编辑器；按用户规则未执行随机生成、PIE 或行走测试，实际进入地牢与病床碰撞由用户体验确认。
