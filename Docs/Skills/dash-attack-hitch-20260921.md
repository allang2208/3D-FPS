# 冲刺攻击群怪卡顿排查 · 2026-09-21

用户现象：面对复数怪物时，攻击前明显卡顿。本次授权范围是冲刺攻击的卡顿排查与优化；不改全局画质、伤害、技能成本、60°扇区、击退或动画时序。

## 已发现的调用开销

1. `TickDashReadiness` 与 HUD 使用的 `DashReadyFraction` 原来都调用 `DashAttackStats` 取一个准备时间。后者会调用 `ColdSteelMelee::Evaluate`，再评估武器配件、强化、附魔、属性、伤害构成、普攻攻速以及快速进战数值。连续奔跑时这些完整计算每帧重复至少两次，左键判定还会再调用。这与怪物数量无直接关系，但给动作入口增加了重复工作。
2. `QuerySector` 对每个目标调用 `RuneSwordWorldOccludes`。旧遮挡查询从零开始，先遇到前排Pawn，将该Pawn加入忽略，再重新发射同一条射线，依次跨过所有前排敌人。群怪在同一走廊中密集排列时，N个目标的遮挡射线次数可接近 N×(N+1)/2。这是源码可直接定位的群怪放大因素；尚无实测证明它是本次卡顿的唯一原因。
3. 下劈结束的技能修炼会走同步档案提交，击杀也可能触发存档和掉落加载。刚才日志中有怪物击杀、掉落／武器图标准备和资产等待，因此不能仅凭现象排除这些后续开销。本轮未擅自修改奖励或存档事务。

已排除的直接路径：`SpendStamina` 和 `ReduceAllAbilityCooldowns` 仅更新运行时数据，没有在出招入口同步写盘。`Overhead` 动画引用在装备时加载，发动函数不另行调用 `LoadObject`；仍需运行数据判断首次姿态求值／渲染开销。

## 优化

- 在冲刺组件内直接用技能定义和当前等级计算准备时间；HUD与连续奔跑Tick不再评估整套武器。正式发动依然获取当前装备和buff数值，避免缓存造成增伤或消耗过期。
- 扇区查询一次收集范围内可以穿透的Pawn，共享一份忽略列表；每目标先直接判断世界遮挡。只有射线碰到宽阶段集合之外的额外Pawn，才建立私有重试列表。
- 保留墙壁等实体遮挡，以及原来普通刀路查询的逐Pawn穿透语义。没有减少有效目标数或拆帧结算伤害。
- 已死亡怪物在扇区几何／骨骼最近点查询之前排除；原伤害结算本来也跳过这些尸体。
- 增加 `DashAttack_Entry`、`DashAttack_Contact`、`DashAttack_SectorQuery` CPU trace区段。单次入口或接触超过4ms时输出 `[DashAttackPerf]`，分别列出出招数值计算、StartSwing、停止移动，或者扇区查询与实际伤害结算的毫秒数。正常快速路径不输出日志。

修改文件：

- `Source/FPSGAME/Weapons/RuneSwordDashAttack.cpp`
- `Source/FPSGAME/Weapons/RuneSwordHitQuery.cpp`

## 已执行的检查与边界

运行日志来源：`Saved/Logs/FPSGAME_2.log`，用户在 `DayNight_Lighting` 地图中的PIE记录。日志没有原冲刺动作的分段耗时，因此无法提供修改前的该技能帧耗时。

通过项目串行桥读取运行环境：先连接到PID35464，无运行中的GameWorld；检测到另一个编辑器节点后尝试连接，该节点随后不可达。没有主动创建或结束用户PIE，没有改玩家位置、消耗资源或新增怪物。

必要Live Coding构建被独立角色身体模块错误阻塞：`Source/FPSGAME/Characters/FPSPlayerBodyComponent.h:39` 的反射属性使用 `TMap<TObjectPtr<UMeshComponent>, TArray<TObjectPtr<UMaterialInterface>>>`，UHT不支持容器直接嵌套。错误在本轮源文件编译之前发生。保留该文件，未修改其他任务内容。桥接回执：`SourceAssets/DashAttack20260921/compile-perf-01.txt`。

随后使用当前UE Editor目标生成的MSVC响应文件，重定向obj、依赖和诊断输出到本任务独立目录，单独编译本轮两个实际翻译单元。`RuneSwordDashAttack.cpp`、`RuneSwordHitQuery.cpp`均通过，exit code 0；没有链接或替换正在使用的DLL。命令及响应文件：`SourceAssets/DashAttack20260921/CompileOnly/`。

当前交付：源码优化与独立编译完成，未加载本次补丁；没有真实群怪场景前后耗时对比，不宣称已消除卡顿或给出FPS收益。完整构建阻塞消除后，需在同地图、同敌人数量／位置下记录若干次冲刺攻击，读取 `[DashAttackPerf]` 区分出招、范围查询、伤害／击杀结算；如峰值仍在damage_ms，再针对同步奖励／掉落路径继续处理。
