# 3P NPC 曲柄双手工具刚性绑定、PCHIP 动力链挥动与实测家具坐姿

本页沉淀自 `LumberMillOps-R58 / R60 / R61`（`A_LJ_SplitLog_Loop`、`A_LJ_ChopTree_Loop`、`A_LJ_SawLog_Loop`、`A_LJ_SitTavern_Relaxed`），适用于基于 `SKM_Jason_body_Skeleton` 的村镇/营地 3P 工作与休闲 NPC 动画。

## 1. 曲柄双手工具的实测刚性契约（杜绝错位与滑移）

1. **禁止假设握柄为直线 `X = 0`**：真实扫描/写实工具（如 `SM_BattleAxe`）木柄存在显著弯曲（`-6.29..-2.19 cm`）。制作前必须按 Z 分层切片实测下/上发力区的真实截面质心与半径。
2. **唯一刚性 `hand_r` 绑定**：不要在运行时每帧按左右手浮动位置重算工具朝向（必然引起掌心滑移和腕部错位）。改为由制作脚本从实测握点、旋前内包（`~44°`）与掌纹斜握（`~42°`）导出唯一常量 `ToolInHandR`，运行时只执行 `ToolWorld = ToolInHandR * BodyMesh->GetSocketTransform("hand_r", RTS_World)`，多条同工具动作共享同一契约。
3. **十指圆柱贴面与副手镜面**：调用 `FitShaft` 按握柄实测半径逐指贴合（双拇指朝斧头方向锁在食指外侧），并以 2-Bone 铰链平面 IK 令左右手全帧触达误差 `= 0.000 cm`、副手握点偏移 `= 0.000 cm`。
4. **保留 MetaHuman 后处理扭转骨**：`SK_Smith_Body` 带 `ABP_Smith_R4_Correctives`，脚本**严禁覆盖 `upperarm_twist_01` / `lowerarm_twist_01/02`**，否则会抹除绑定扭转角并破坏腋下/前臂形态。

## 2. 周期 C1 PCHIP 动力链挥动（消除机械分段感）

1. **废除逐段归零 `Ease(T)`**：分段缓动会在每个关键帧把速度归零，产生僵硬机器人感。循环工作动作改用周期 C1 单调三次插值（`eval_periodic_pchip`）。
2. **髋先动 + 胸滞后甩鞭 + 椭圆收势**：蓄力顶点之后髋/躯干提前 `2–3` 帧启动下压，双手与工具滞后甩鞭过顶下劈；命中帧落在**精确整数帧**并与 C++ 粒子/音效/裂木相位（`Crossed(u)`）1:1 对齐；收势沿侧面椭圆 S 弧回拉，绝不沿劈砍直线倒放。

## 3. 实测家具休闲坐姿规范（避免复用错高度凳姿）

1. **先测真实家具三基准再做动作**：在无头 UE 读取目标场景的真实 `FloorZ`、坐面顶高 `SeatTopZ`（如 `SM_TavernStool = 46.06 cm`）及邻近桌面高/前距（`SM_TavernTable = 76.07 cm`）。
2. **胶囊接地与三点接触**：`Actor.Z = FloorZ + CapsuleHalfHeight`（`88.0 cm`）确保靴底 `0.0 mm` 贴地；骨盆重心按实测 `SeatTopZ` 落座；双脚做自然非对称错落（一脚前伸外展、一脚微收），一手前臂松弛搭桌面（避开桌面碗勺 `>= 14 cm`）、另一手搭同侧大腿中上段，叠加 `4.0 s` 周期呼吸与微幅环顾。

## 4. 参考实现

- 生产脚本：`Tools/WorldGeneration/ForestVillage/author_lumber_ops_r60.py`、`author_tavern_sit_r61.py`
- 运行时刚性绑定与相位反馈：`Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp`
