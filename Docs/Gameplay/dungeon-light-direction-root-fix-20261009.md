# 随机地牢光源实际方向修复（2026-10-09）

**本次交付已被后续用户截图证伪。** 下述第一次修复把最终姿态设置放在 `Movable` 之前，游戏世界拒绝旋转；空编辑器世界检查没有覆盖该限制，隔离渲染的调用顺序也与当时生产代码不一致。完整原因、正确顺序和新的已初始化游戏世界证据见 [移动性设置顺序修复](dungeon-light-mobility-order-fix-20261009.md)。以下内容保留作历史记录，不代表最终修复状态。

用户截图指出吊灯仍把强光打到天花板。此前仅检查配方与作者样板，漏掉了原生运行时创建灯光的变换行为，不能据此认定正式随机地牢方向正确。本轮检查实际创建出来的灯组件，并修正生成器。

## 根因与修改

本机 UE 的 `ASpotLight` 构造函数已把根组件设置为 Pitch -90°。`AActor` 的默认原生创建路径将根组件默认变换与请求的创建变换相乘。旧生成器再次传入 Pitch -90°，因此真实组件的局部 +X 发光方向成为世界 `(-1, 0, 0)`，即水平，而非配方要求的 `(0, 0, -1)`。宽锥角可以覆盖光源上方区域。

引擎依据：`Engine/Private/SpotLight.cpp` 中 `SpotLightComponent->SetRelativeRotation`，`Engine/Private/Actor.cpp` 中 `RootTransform * UserSpawnTransform`，`Engine/Private/LightComponent.cpp` 中 `GetDirection()` 返回组件 X 轴。后台进程实际报告版本 `5.8.3-58210709+++UE5+Release-5.8`。

`Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp` 的 `Dungeon.Lights` 创建任务现已：

- 创建完成后明确设置世界位置和完整世界旋转，覆盖原生根组件的默认姿态。
- 将灯具完整 Pitch/Yaw/Roll 与房间变换组合，保留倾斜壁灯、台灯的设计方向。
- 移除后续仅设置 Yaw、丢失 Pitch 的旧分支。
- 将配方的 `spot` 类型与优化开关解耦，关闭优化时也保留定向灯型。

这次修复位于运行时生成器，不改灯具、房间布局、光源数量、流明换算、半径、阴影预算或故障闪烁调度。正式项目的 Lumen / 光追设置没有修改。

## 逐灯检查

`probe_spawned_directions.py` 在独立、未保存的空世界中，通过原生 deferred spawn 创建真实灯组件；绕开会重新设置姿态的编辑器 Actor 工厂。每条配方分别检查房间旋转 0/90/180/270°，记录旧分支的实际方向，再记录显式世界变换后的实际方向。

- 当前目录 328 条光源：283 矩形光、45 聚光灯；共 1,312 个真实创建与方向读回案例。
- 45 条聚光灯配方的旧运行时方向偏差 90°，四种房间朝向均重现；修正后的方向与设计相符。
- 另检查 4 组带非默认俯仰、偏航、翻滚的聚光灯旋转，最终发光方向正确。
- 此探针检查原生创建语义及相同修正操作，没有运行完整地牢生成流程或 PIE。
- 独立重新加载 4 张已保存地图，读回固定起始区 13 盏、两个连接大厅样板各 53 盏、接待大厅样板 23 盏，共 142 个现有灯组件。位置、灯型和实际发光方向与对应灯具配方相符；这些保存组件没有原生创建时的额外旋转。记录见 `saved-component-directions.json` 和 `saved-component-directions-2.log`。

| 受影响模块 | 聚光灯数 |
|---|---:|
| Distribution | 1 |
| Drainage | 2 |
| ShoredBreach | 1 |
| Junction | 2 |
| Transit | 1 |
| VentilationLoop | 2 |
| FreightTransfer | 3 |
| BossConfluence | 2 |
| BossPumpHall | 9 |
| ForkLeft / ForkRight | 各 2 |
| FreightTransfer_WarehouseLink | 3 |
| FacilityReceptionHall | 6 |
| FacilityTransit | 9 |

逐盏、逐房间朝向的记录：`SourceAssets/DungeonLightDirection20261009/Receipts/per-light-directions.csv`；原始引擎读回：`native-spawn-directions.json`。

## 隔离光照对比

`DungeonLightDirectionCommandlet` 创建临时房间，以同一盏灯、固定机位、固定曝光、固定亮度作前后比较，仅改变最终旋转。使用项目已有的 GPU staging 读回方式导出，未保存地图。

- `Receipts/NativeRender/before.png`：实际方向 `(-1, 0, 0)`；主光束落在侧面的墙与远端地面。
- `Receipts/NativeRender/after.png`：实际方向 `(0, 0, -1)`；主光束回到吊灯下方的地面。
- 对比使用直接光隔离方向问题，不是用户截图所在接待大厅的同机位复现，也不代表整场景视觉验收。此隔离房间中灯罩遮挡了上方直射光，不能用它声称复现了截图中的天花板光斑。
- 首次 Python RT 导出的全黑图片无效，不作证据。该无效导出器及其输出于 2026-10-13 移入 `trash/scene-lighting-retired-20261013/SourceAssets/DungeonLightDirection20261009/`，原路径、散列和替代物见 [归档清单](../Publication/SceneLighting20261013/retired-files.json)。

普通 `FPSGAMEEditor Win64 Development` 构建已成功，修复已链接进正式 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。构建与渲染日志见本轮 `Receipts`；源码、目标文件和 DLL 的时间及 SHA256 见 `build-and-direction-summary.json`。没有主动开启 GUI 编辑器、重启现有编辑器或运行游戏，整场景体验仍由用户确认。
