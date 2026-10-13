# 大厅顶棚强光仍然存在：移动性设置顺序修复

用户在加载新 DLL 后再次提供大厅顶棚强光截图，证明上一轮修复没有在游戏中生效。本轮直接读取该次游戏日志，定位到 UE 拒绝移动 Stationary 根组件；不是未重启，也不是调低亮度可以解决的问题。

## 第一次修复为何失效

上一轮正确识别了聚光灯默认 Pitch -90° 与创建姿态叠加的问题，但代码顺序仍然是：

1. 原生创建 `ASpotLight`，默认根组件为 Stationary。
2. 设置最终位置和旋转。
3. 切换根组件为 Movable。

`USceneComponent::CheckStaticMobilityAndWarn()` 在已初始化的游戏世界中拒绝第 2 步。用户该次 Seed `589106240` 的游戏日志含大量 `SpotLight_*` 的“移动性必须为可移动”告警。因此运行时仍保留错误的水平光束。

此前空编辑器世界的 1,312 次检查没有触发游戏世界的移动限制；第一次隔离渲染又提前设置了 Movable，与当时生产代码的顺序不一致。这些结果不能证明当时的运行时修复成功。原始日志摘录保存在 `SourceAssets/DungeonHallCeilingLight20261009/Receipts/original-game-mobility-warnings.txt`。

## 正式修复

`Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp` 现先取得灯组件并设置 `Movable`，然后设置最终世界姿态。保持灯具配方、灯具网格、光源数量、亮度、房间布局和故障闪烁策略，不修改全局 Lumen / 光追。

用户无法回到大厅配合读取，因此继续使用后台复现；没有启动或关闭用户的编辑器。

## 游戏初始化状态下的逐灯检查

扩展现有 `DungeonLightDirectionCommandlet` 的 `-ProbeGameDirections` 分支，采用已完成 `InitializeActorsForPlay` 的 GamePreview 世界。检查明确要求：`IsGameWorld`、`bIsWorldInitialized`、`AreActorsInitialized` 和每盏灯的 `IsActorInitialized` 均成立。

逐条创建 328 条配方，在 0/90/180/270° 房间朝向下读取真实组件方向，同时记录 `SetActorLocationAndRotation` 是否被引擎接受：

- 总计 1,312 个案例。
- 旧顺序错误 180 次，对应 45 条聚光灯配方的四种朝向。
- 修正后错误 0 次，所有最终变换均被接受，方向与配方一致。

原始结果：`Receipts/initialized-game-directions.json`；逐灯表：`Receipts/per-light-game-directions.csv`；成功日志：`Receipts/initialized-game.log`。

## 大厅画面复现

同一 commandlet 的 `-ReceptionHall` 分支读取正式目录中接待大厅的 149 个模型部件和 23 条灯光配方，保留灯具位置、颜色、光输出、锥角与投影规则。旧顺序与新顺序使用同一镜头、同一曝光，后台导出前后画面。

这是正式大厅几何与直接光的隔离复现：不包含玩家、完整地牢运行和 Lumen 间接光；为固定对比也未播放灯具故障光函数。不能冒充用户截图同一游戏帧，也不能证明间接照明为绝对零。

本次已完成渲染并查看图片：旧顺序在大厅左上方顶棚形成明显亮斑；修正后的同机位中该直射亮斑消失，主光束转到下方地面。两张图只改变灯的最终方向，未调整灯光亮度或曝光。

- 修正前：`SourceAssets/DungeonHallCeilingLight20261009/Receipts/HallRender/before.png`
- 修正后：`SourceAssets/DungeonHallCeilingLight20261009/Receipts/HallRender/after.png`
- `hall-render.log` 记录旧旋转 `move_accepted=0`、`initialized=1` 与最终 `DIRECTION_PREVIEW PASS`，进程退出 0，无材质编译错误或默认材质回退。

## 构建与交付

普通 `FPSGAMEEditor Win64 Development` 构建成功，修复已链接进正式 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。见 `Receipts/native-build-2.log`；源码、目标文件与 DLL 的时间及 SHA256 见 `Receipts/completion.json`。没有重写正式地图或重置用户的游戏进度。
