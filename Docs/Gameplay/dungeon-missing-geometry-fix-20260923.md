# 地牢运行时缺失几何与地面碰撞修复

## 故障与证据

2026-09-23 用户反馈：入口走廊仍可见，随机生成区域黑屏，走出入口会坠落。

故障日志 `Saved/Logs/FPSGAME-backup-2026.09.23-05.09.09.log` 在 05:07:51 UTC 大量报告：在移动性为静态的 `StaticMeshComponent0` 上调用 `SetStaticMesh`。随后 05:07:54 的 `AuthoredDungeon` 日志却报告 seed `300551968`、299 个模块、1,937 个独立刚性部件且状态为 `ready`。

UE 5.8 本机引擎源码 `StaticMeshComponent.cpp:2374` 明确拒绝在已开始游戏、已注册且为 Static 的组件上设置新网格，直接返回 false。`AStaticMeshActor` 经普通 `SpawnActor` 创建时，默认静态组件已注册；生成器忽略了赋值失败，仍累计部件数量并释放玩家。这同时解释了渲染几何和地面碰撞缺失，而原有入口仍在。

## 修复范围

`Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp` 的网格创建步骤改为：

1. 将新建部件纳入原有暂存/回滚管理，解除组件注册。
2. 设置网格、导航参与、材质、移动性、碰撞和阴影；实例组件先添加首个实例。
3. 完成配置后统一注册组件，创建对应渲染与物理状态。
4. 核对实际网格引用和注册结果；失败写入生成错误，交由现有回滚与加载失败流程处理，不再报告准备完成。

保留刚性结构最终 Static、液体 Movable、实例分组、房间随机布局及装饰物避让规则。没有增加覆盖全图的替代地板。

## 交付状态

源码修复已完成。2026-09-23 13:17 当前编辑器的 Live Coding 返回 `Result: Success`；本次 `AuthoredDungeonGenerator.cpp.lc.obj` 的时间为 13:16:45。结果保存在 `Saved/DungeonMeshSpawnFix20260923/compile-python-result-2.txt`。

此次没有重新打开编辑器，也没有改写地图资产。已生成的空房间不会因函数热补丁自动重建，需要退出并重新进入地牢。基础 `UnrealEditor-FPSGAME.dll` 仍是原常规构建，当前结果属于会话热补丁；下次关闭编辑器后应执行 `Tools/Build/Build-Editor.ps1` 将源码固化进常规 DLL。当前编辑器与另一个资产 commandlet 正在占用工程，没有强行关闭它们。

已核对故障日志、引擎拒绝赋值的条件和编译结果；尚未重新进入地牢进行画面及行走复测。

后续状态（2026-09-23）：用户已反馈实测无缺失场景/坠落问题，随机房间和 Boss 战斗正常。在随后灯光、栏杆、杂物优化回合中，常规 Editor 构建完成，`UnrealEditor-FPSGAME.dll` 更新至 15:01:27，本修复已随常规 DLL 落盘，不再仅依赖上一会话热补丁。新一轮视觉修改的范围与交付见 [后续优化记录](dungeon-boss-light-rails-clusters-20260923.md)。
