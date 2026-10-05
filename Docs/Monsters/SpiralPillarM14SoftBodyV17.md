# 螺柱 M-14：XPBD 软体死亡 V17

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-05。用户否定此前死亡效果：下沉、扭曲，要求按 GitHub 软体方案调整。V14 的形变插值与 V06 的最终单刚体交接不再作为这只怪物的目标死亡驱动。

## 实现

- 同一外观表面制作专用尸体驱动网格：保留 1,080,412 个源顶点、1,936,942 个三角形和原 UV，不删面、不修改活体 V15 网格及其动作。
- 24 cm 代理网格共 523 个软组织节点、1,620 个四面体；原外观按正重心权重绑定在四面体内，避免远处骨骼拉动局部碎片。焊接位置的材质切缝共享绑定。
- 8 组金属区域用 32 个模拟点形成刚性框架，独立旋转和局部连接。实际表面方向极值点用于接地支撑，保持铭牌及链条区域的形状。
- 从死亡时的当前骨骼姿势初始化代理，关闭原网格动画、死亡 Morph 和最终刚体移交；由一个求解器负责整个死亡过程。死亡是自由运动的模拟结果，没有固定的压扁目标。
- XPBD 距离、带符号体积约束，体积反转限制和 1.28 倍边长上限；软组织有基于空间散列的节点自碰撞。金属每轮恢复刚性形状。
- 全部节点先取得世界地面支撑；运行中每帧最多刷新 64 个节点，并扫掠它们的运动路径。约束子步持续使用支撑平面，静止后保存当前形状，不再整体下移尸体根节点。
- 使用专用尸体材质副本，从形变后的表面重建切线框架并继续采样原法线贴图。活体材质和 V16 绿色毒液保持原引用。

## 集成与成本边界

入口 `ASpiralPillarM14::PresentState` / `TakeDamage`；`UM14SoftBodyDeathComponent` 由现有角色死亡 Tick 推进，没有活体时期的新 Tick。新增 `UM14SoftBodyData` 保存代理、初始姿势映射和专用尸体网格引用。

按 1/120 s 固定子步计算，每帧最多 6 个子步，每个子步 10 轮约束。并入既有 `UHumanoidRagdollBudget`，每只软体预留 32 个预算单位（不是 32 个 Chaos 刚体）；默认同屏新尸体准入上限仍为 4。预算满时保留捕获姿势等待空位，不退回旧形变塌陷；已有接地低速尸体可释放预算。体积模拟不直接对约 194 万个显示三角形逐帧计算或回读。

接地且均方速度低于阈值持续 0.7 s 后定姿，角色 Tick 和求解停止，保留原 20 s 尸体寿命。模拟属于本地外观；死亡、掉落/经验、伤害和状态仍由服务器决定。不同客户端的软体姿态不逐点网络同步。尸体显示组件不产生玩家阻挡；世界支撑采用地形/场景查询。

这是有界代理模拟：节点球形自碰撞和缓存接触不等同于逐显示三角形连续碰撞；预算拥挤时可能延后塌落开始。实际形变、接地和性能没有做游戏测试，不能据构建成功宣称视觉问题已验证消失。

## 上游与制作源

采用 [PositionBasedDynamics](https://github.com/InteractiveComputerGraphics/PositionBasedDynamics) 的 XPBD 距离/体积约束核，适配 UE 的向量类型、柔顺度、体积梯度与步长。没有安装整个外部物理引擎，也没有把 Chaos 替换掉。MIT 许可全文、上游源码快照和 SHA-256 位于 `Source/ThirdParty/PositionBasedDynamics/`。

- `Tools/SpiralPillarM14/author_xpbd_cage_v17.py`：生成代理、重心绑定、可编辑 OBJ/JSON 和上游来源记录。
- `Tools/SpiralPillarM14/import_xpbd_corpse_v17.py`：调用原生制作接口，保存网格、骨架、材质、数据与正式蓝图。
- `Source/FPSGAME/Monsters/M14SoftBodyAuthoring.cpp`：在网格源描述中制作专用绑定，保留表面与 UV。
- `Source/FPSGAME/Monsters/M14SoftBodyDeath.cpp`、`M14XPBDConstraints.h`：运行时接管、求解与姿态提交。
- `SourceAssets/SpiralPillarM14Meshy20261004/ProductionV17/Authoring/M14_SoftProxy_v17.obj` 与 `Exports/cage.json`：可编辑代理源；原详细表面继续来自 V15 的 Blender 文件。

## 交付状态

Editor / Game 必要构建已完成，两者退出码均为 0。后台资产命令完成并退出 0；专用尸体网格 `SK_M14_XPBDCorpse_v17`、骨架 `SKEL_M14_XPBDCorpse_v17`、代理数据 `DA_M14_XPBDCorpse_v17`、四个专用材质和正式 `BP_SpiralPillarM14` 共八个资产已实际保存。蓝图 `SoftBodyDeathData` 已引用新数据。

实际保存回执位于 `ProductionV17/Records/ue_revision.json`，`complete: true`。导入最终日志为 `import_ue_04.log`；此前三个导入中断分别为 Python 骨架赋值/属性暴露问题，已处理。未打开游戏、未运行自测或验收渲染，待用户体验。
