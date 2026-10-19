# 医疗区第三房缚群未出生：接地间隙修复

用户反馈：悬钟已出现，第三房缚群没有刷新。

## 原因及证据

已有游戏日志记录医疗区遭遇启动，第三房配置了 14 名员工和 3 个特殊名额，但没有缚群成功出生的记录。正式缚群蓝图加载成功，胶囊半径/半高均为 **225 cm**，导航规格为半径 225、高 450 cm。

`FacilityHallEncounter::FindSpawn` 原来用 `Radius + 3` 扩大胶囊检查范围，中心却仍在 `GroundZ + HalfHeight + 3`。缚群因此使用半径 **228 cm**、半高 **225 cm** 的查询形状。UE 的 `FPhysicsShapeAdapter_Chaos` 在半径不小于半高时改用球体，查询球的底部正好落在地板上，没有原本期望的 3 cm 间隙。地面重叠检查拒绝了槽位，后续继续重试同样错误的计算。

悬钟通过 `AM09CeilingRoute::FindPlacement` 查找顶面，不经过这个地面胶囊检查，故能正常出现。该问题不属于第三房漏配首领，也不应通过缩小缚群、停用碰撞或伪造击杀解决。

针对用户反馈，使用正式保存的第三房 20 个碰撞网格，在独立初始化物理查询世界中复现。没有 BeginPlay、怪物实例、AI、战斗、PIE 或地图保存。81 个候选点对应当前唯一足够容纳缚群的中央出生格，局部 X=-135..135、Y=105..375 cm。

| 查询 | 结果 |
| --- | --- |
| 向下地面射线 | 81/81 命中 |
| 故意穿地 5 cm 的对照形状 | 81/81 被阻挡，确认查询世界有效 |
| 原出生检查 | 0/81 通过；81 个点被 `SM_AnatomyTheatre_Paving` 阻挡，另有 9 个也触及 `SM_AnatomyTheatre_Floors` |
| 修正后的出生检查 | 81/81 通过，无碰撞阻挡 |

最初 Python commandlet 加载的编辑世界没有有效物理查询，故连穿地对照也未命中；该结果标为无效，未作为通过证据。随后改用初始化查询世界得到上述结果。此处只复现和检查地面/碰撞，不代表生成后的导航、实际战斗与联机已验收。

## 修改

共用地面出生检查采用：

```cpp
ClearanceRadius = Radius + 3.f;
ClearanceHalfHeight = FMath::Max(HalfHeight, ClearanceRadius);
Location.Z = GroundZ + ClearanceHalfHeight + 3.f;
```

缚群查询形状变为 228/228 cm，查询中心离地 231 cm，恢复完整 3 cm 查询间隙。实际怪物胶囊仍是原生 225/225 cm；落地由现有角色移动处理。普通细长胶囊的高度计算不变，同一检查中其他近球形胶囊也能保留正确间隙。

不修改怪物资产、第三房编成、病房螳螂修复、悬钟逻辑、出生重试身份或击杀缚群开门条件。

上轮全面排查的范围/掩码核对没有覆盖该真实碰撞情形，这次通过用户反馈补齐了诊断。

## 文件及落盘

- 生产修改：`Source/FPSGAME/Dungeons/FacilityHallEncounter.cpp`。
- 专项诊断：`Source/FPSGAME/Development/MedicalBossSpawnDiagnosisCommandlet.h/.cpp`，通过显式命令运行，不接入游戏循环。
- 工具：`Tools/MedicalBossSpawnFix/`。
- 证据、原文件和构建回执：`SourceAssets/MedicalBossSpawnFix20261018/`，主要为 `current_inputs.json`、`theatre_module.json`、`collision_probe.json`、`observed-medical-log.txt`、`build-FPSGAMEEditor.json`、`build-FPSGAME.json` 和 `delivery.json`。

Editor、Game 均已完成后台常规构建，退出码均为 0。只保存源码与构建产物，没有修改地图或怪物包。未自动打开编辑器或运行游戏，实际出生与战斗由用户测试。
