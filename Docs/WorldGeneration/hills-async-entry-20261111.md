# 温带丘陵入场等待与异步生成调整

## 现场与原因

用户报告进入温带丘陵超过 200 秒，截图显示 256 秒、82%，状态为“正在布置附近植被 82/171”。本轮只读取现有运行日志和源码，不重新启动游戏或编辑器复现。

`Saved/Logs/FPSGAME.log` 的 2026-11-11 18:03 记录显示：

- 恢复种子 `-1871694467`、GeneratorVersion=1、6 条地形修改；这是继续同一个世界，不是每次重抽地图。
- 出生区 9 个地表格约 4.15 秒就绪；河流与两处浅潭也已经生成。
- 12 个环境资产加载阶段在约 22.30 秒完成。
- 入场条件随后等待约 96 m 范围内的全部四层 PCG，截图中的 171 格包括大量草地和林下装饰。运行时虽已有异步地形任务和 PCG 分帧调度，这个等待条件仍把背景工作变成了入场前置条件。
- 同一编辑器日志还出现武器骨骼资产处理与同步等待，部分操作长时间占用同一个帧。这会进一步拖慢游戏调度；本次未修改或干预这些制作任务。

本批保留的证据为 `SourceAssets/HillsAsyncEntry20261111/Receipts/entry-before.log`；截图来自用户。旧源码备份已移至 `trash/hills-async-entry-20261112/SourceAssets/HillsAsyncEntry20261111/Backups/TemperateHillsStreaming.cpp`。

## 修改范围

加载行为修改集中在 `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp`：

1. 入场地形等待范围由 96 m 调整为 32 m，仍保留初始 3×3 地表格、真实碰撞完成、树干碰撞、地面材质可渲染和高清纹理驻留检查。
2. 入场只激活树木、岩石两层，等待角色周围 16 m 内相交的对应 PCG 分块；缺失格仍算未完成。树木／岩石使用 64 m 格子，等待格数随角色位置变化，按格边界统计，不是把树木裁到 16 m。
3. 灌木／幼树／蕨类和草地层在加载界面释放玩家输入后逐层启用，间隔 1 秒，继续使用原 PCG 预算调度。若用户选择完整资源准备模式，也不会在其输入锁定阶段提前加入这些装饰层。
4. 保留正常游玩的地形视野半径、各层 PCG 生成／清理半径、材质渐隐距离、植被密度、避让规则、风动和水体接入。只改变入场等待范围和层的启用时序。
5. 编译等待改为当前环境资产批次及本场景预热材质；PSO 等待改为本场景预热组件，避免无关编辑器任务的全局队列持续挡住丘陵入口。
6. 进入后仍保持地形线程池数值计算、每帧有限提交与前沿碰撞保护。PCG 的 UObject 访问和实例提交保持游戏线程分帧，不将不安全的 UObject 操作直接移入工作线程。

未修改存档格式或玩家存档。退出并重进仍按已有种子重建附近运行时实例，并恢复地形／采集等状态；不把整张程序化场景保存为巨大静态地图。新增 `HILLS_ENTRY_SOLIDS` 与 `HILLS_BACKGROUND` 日志，方便下次从实际进场日志区分必要准备和后台生成。

## 交付状态

用户保存并关闭编辑器后，按项目批次互斥完成后台构建。`FPSGAMEEditor Win64 Development` 于 18:24:07 成功，UBT 确认目标已是最新；`FPSGAME Win64 Development` 于 18:28:21 成功，完成 193 项编译／链接动作。退出码均为 0，回执为本批次 `Receipts/FPSGAMEEditor-build.json` 和 `Receipts/FPSGAME-build.json`。构建产物已落盘，后续正常启动加载新版。

首次完整构建同时发现 `Weapons/GunsmithSystem.cpp` 第 115 行的 UE JSON 共享字符串键不能隐式传入 `TArray<FString>::AddUnique`。按该文件第 95 行已有写法改为 `FString(*Slot.Key)`，仅补显式转换，未修改槽位或枪械行为。修改前文件已移至 `trash/hills-async-entry-20261112/SourceAssets/HillsAsyncEntry20261111/Backups/GunsmithSystem.cpp`；失败日志为 `Receipts/FPSGAMEEditor-20261111-181455-output.log`。

本轮没有重建材质或地图，没有使用 computer use，也不主动重开编辑器／运行游戏。未测量修改后的实际入场秒数、行走流送或帧率；不将缩小等待集合换算成未经实测的加载时长。

当前版本的等待范围、完整档和联机准备顺序见[后续入场整理](../Publication/HillsAsyncEntry20261112/README.md)。
