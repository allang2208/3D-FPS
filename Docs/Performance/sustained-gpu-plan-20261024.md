# 随机地牢持续低帧：实施方案与本轮修改

日期：2026-10-24。目标保持画质、怪物数量、战斗规则和动画更新规则；只做后台源码修改与必要编译，不启动 UE、游戏、commandlet 或测试。

## 方向与证据

用户明确症状是“每次进入一个新场景，开始进入刷怪时就会持续低帧”。创建对象、首次编译和每帧渲染是不同问题。此前准备池、鼓囊 GPU 准备和大厅波次修正继续保留；本轮不再扩大准备池来处理持续渲染。

已有 2026-10-22 采集在首波后的 5–10 秒中，Graphics GPU Frame 平均约 64.05 ms，已提交 GPUWork 与该窗口的交集约 61.75 ms；玩家装备与怪物形变一起变慢，最低本地显存预算余量约 126 MiB。这是旧版本的持续 GPU 慢态证据，不是本轮性能结果，也不能证明某个资源被换出。当时 WDDM 启动权限失败，物理驻留与调度因果尚未闭合。

完整的既有生成链路和 GitHub 调研见 [大厅生成与方向分析](hall-spawn-smoothness-and-direction-20261024.md)。通用对象池可以借鉴分帧创建、异步资产和明确的激活/回收接口，但不能消除已生成怪物每帧的蒙皮、毛发、光追和阴影成本。

## 本轮实施一：移除完全被替代的原身体渲染对象

`modular_outfits.json` 的世界身体配方用模块化身体和衣物承担显示，并隐藏原身体的所有材质区段。原身体还承担骨骼动画和挂点，不能直接隐藏、注销或停止动画；但原先仍会创建自己的骨骼 GPU 渲染对象。

新增 `UFPSPlayerBodyMeshComponent`，作为角色原身体组件的派生类型。模块化配方提交完毕后，逐 LOD、逐渲染区段确认原身体全部被隐藏，才进入只提供姿势的模式：

- 保留组件注册、动画、骨骼刷新、碰撞、挂点与 follower pose；不更改原身体的可见性/阴影标志，衣物的可见性同步仍按原路径工作。
- 停止创建这份原身体的 skeletal mesh object / scene proxy，释放重建过程中暂存的旧 GPU mesh object。模块化身体和衣物照常渲染。
- 原身体有可见区段，或者有布料模拟实例、默认 mesh deformer、胶囊阴影时，不进入该模式。
- 装备恢复原身体区段、模块化配方释放或切换时，恢复原身体渲染；替换为其他源 mesh 也不沿用旧 mesh 的抑制标记。
- 不影响第一人称的常驻姿势锚点组件；那个组件是上一轮已经完成的单独路径。

适用范围是“全部原身体区段确实已被替代”的玩家世界身体，不是删除可见身体/衣物，也不是减少怪物实例。减少的是这一份重复渲染对象及其可能提交的蒙皮、光追和阴影工作；节省多少需由运行数据确认。

涉及源码：

- `Characters/FPSPlayerBodyMeshComponent.h/.cpp`
- `FPSGAMECharacter.cpp`
- `Characters/FPSModularOutfitComponent.cpp`
- `Characters/FPSPlayerBodyEquipment.cpp`

## 本轮实施二：补齐已有 F6 的持续渲染记录

原有详细形变记录只覆盖无面研究员和接待员的主身体，不能代表整个怪群，也看不到随怪群一起变慢的玩家装备。现在只在用户主动开启 F6 GPU 采集时扩大记录：

- 当前 World 的 FPSGAME 玩家，以及拥有 MonsterCombatComponent 的 Character；包括它们的骨骼/poseable 身体、附件与 Groom。玩家优先，骨骼组件最多 96 个、Groom 最多 32 个，超限明确记录。
- 保留原 `staff` 数据兼容旧读取工具；新增 `skinned_components` 和 `grooms`，导出 schema 升为 13。
- 骨骼组件记录姿势来源、注册/Tick/可见性/阴影/光追标志、布料和 deformer 状态、原身体只供姿势的模式、实际 render object 是否存在及对象/RT skin cache 的变化。
- 在没有并行动画写入时，比较相邻两个采样点的 CPU 骨骼姿势、Morph 权重/索引和组件变换；同时记录 CPU 骨骼版本与预测 LOD。遇到并行动画直接跳过，不等待它完成。
- Groom 记录组件、资产、绑定、父组件、相对变换、隐藏阴影、LOD 配置、Niagara 激活数量，以及每个 group/LOD 的 `IsSimulationEnable` 结果。这样可以识别重复候选和“调用关闭模拟，但覆盖开关未生效”的配置。
- 沿用最多 2 Hz、360 条完成记录；新增详细比较只在主动 GPU 采集期间保留，停止/清空/离开 World 时释放。记录收集与 RHI 元数据观察耗时。

两个采样点姿势相同，不等于中间所有帧都相同，也不能证明布料、WPO、deformer、毛发或速度历史可以跳过。Groom 配置和 Niagara 激活状态不等于实际 GPU 执行耗时，强制/期望/可用 LOD 也不等于实际渲染 LOD。以上限制写入导出 JSON。

原 native buffer 观察仍只覆盖 Morph 输入/输出，不冒称覆盖全部 SkinCache、RT、毛发缓冲，更不拿逻辑缓冲大小当物理驻留。本轮不触发采集，不增加 GPU readback、flush、强制驻留、强制逐出或动画等待。

涉及源码：

- `UI/FPSPerformanceDeformationSampling.cpp`
- `UI/FPSPerformanceMetricsResources.cpp`
- `UI/FPSPerformanceMetrics.h/.cpp`
- `UI/FPSPerformanceMetricsExport.cpp`

## 后续决策顺序

本轮完成后，由用户自行运行。如果仍有持续低帧，使用现有 F6 GPU 采集入口覆盖进场前与首波后的持续窗口，导出完整 `gpu-...` 文件夹。先确认 manifest 的 WDDM 权限、丢失事件和文件完成状态，再按时间与 UE trace 对齐。

1. 若主要是资源压力/迁移：按实际资源归属处理常驻引用、重复输出和准备预算，不继续盲目增加池容量。
2. 若主要是稳定昂贵的 GPU 执行：按新增组件身份和实际 pass 定位，消除无贡献实例或错误重建；不能根据总 SkinCache/Hair 耗时就停止活体姿势或毛发模拟。
3. 若持续帧成本已恢复、只剩生成尖峰：再根据已有 Hall.NativeAllocation、Hall.FinishSpawning、Hall.GpuWarmup 标记，把明确昂贵的初始化移到提前准备。完整活体怪物池要逐物种实现 AI、计时器、死亡、奖励和网络状态复位，不能直接套用弹丸池。

不修改 LOD 质量、分辨率、材质、光照、毛发密度、怪物总数、波次条件、AI 更新或战斗数值。本轮源码完成不代表持续低帧已经解决。

## 构建交付

备份、构建脚本、日志及逐目标回执存放在 `Saved/SustainedGpuPlan20261024/`。`FPSGAME Win64 Development` 和 `FPSGAMEEditor Win64 Development` 均已后台编译成功，退出码均为 0；最终回执见该目录的 `completion.json`。Editor 构建等待用户保存并关闭正在运行的编辑器后才开始，本轮没有关闭或启动用户的 UE 进程。未运行测试或画面验收，实测留给用户。
