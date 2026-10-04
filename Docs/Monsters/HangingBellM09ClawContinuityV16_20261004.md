# 悬钟护冠双爪：动作重做与腕部连续性

用户指出旧抓击不像抓击、肩肘手腕不自然，随后从预览指出手部断裂。本次因此同时处理专用动作和原模型拆分留下的连接缺陷。游戏验收仍由用户完成。

## 原因

- V11 在命中阶段把小臂和爪尖抬到肩部上方，双腕再次交叉。站立供体的空间方向不适合悬钟的短上臂、长前臂和抱冠起始姿态。
- V13 的左小臂实际有四个独立连通块，最大的两块分别是手掌和前臂；右侧有四条未闭合边。单独封闭拆分边界并不等于手腕已经连接。
- 原交叠区有手指／腕部碎片残留在身体对象上；身体的部分大跨度扇形补面在手臂展开后暴露。权重平滑可以减轻拉伸，但不能修复这些几何连接。
- 原版抽样姿态中，小臂边长最大额外拉伸约 16 cm。该数值来自 Blender 当前蒙皮的离线排查，不代表实机碰撞或画面验收。

原始 Meshy GLB、V03、V13 和 V15 候选保留。本轮最初的 V15 导入在桥排队时取消，没有写入正式资产。

## 制作方案

1. 使用 V13 分区模型，在小肘／腕部建立连续的权重过渡。
2. 保留原掌部与手指表面，重新建立肩部、肘部、腕部到掌根的连续连接面；原 UV 投射回新表面，近端采用连续解剖权重，远端保留手指归属。模型身份、膜片、眼冠、大支撑臂和骨架保持原系统。
3. 保留原封闭身体表面，移除误留在身体上的交叠碎片，将身体接口保持为躯干蒙皮。中间尝试的前胸重铺面因增加开边而未采用，最终由 `finish_arm_continuity_v16.py` 从原封闭身体恢复并作局部清理。
4. 新动作按悬钟的实际比例编排：解开护冠姿态、双爪前探、向下内扣、平缓回抱。使用连续的肘部弯曲面和小幅腕屈伸。M07 的 Attack_D 仅复用接触加速节奏，不宣称是原版整身动作的直接移植。

## 动作合同

- 时长 1.10 秒，60 fps，67 个采样；原地动画。
- 接触区间保持 0.35–0.55 秒；左侧错开 0.025 秒，结束时双侧回到同一护冠姿态。
- 保留原伤害、2.5 秒冷却、实际掌指胶囊判定、双手命中去重与 V14 远近距离选择。
- 三叠鸣震、群眼凝视、死亡片段及 V13 物理资产不替换。

## 文件与交付状态

- 制作源：`SourceAssets/HangingBellM09Meshy20261003/ArmContinuityV16/Authoring/`。
- 正式重建顺序：`refine_claw_skin_v15.py` → `author_crown_claw_v15.py` → `repair_arm_continuity_v16.py` → `finish_arm_continuity_v16.py` → `export_claw_continuity_v16.py` → `import_claw_continuity_v16.py`。`repair_arm_socket_surfaces_v16.py` 仅保留为未采用的制作实验，不在正式重建链中。
- 导出／导入：`export_claw_continuity_v16.py`、`import_claw_continuity_v16.py`。
- 排查记录：V16 `Records/topology.json` 为修改前；`topology_after.json` 为后续制作排查。姿态渲染在 `CrownClawV15/Inspection/`，`old_*`、`new_*` 和 `v16_*` 分别区分旧动作、过渡候选、连续性修复。
- 最终保存状态以 V16 `Records/import_saved.json` 为准。未运行游戏测试，不以制作预览代替用户体验确认。
- 针对性离线排查：左右小臂分别为 1 个连通网格、0 开边、0 非流形边；身体保持 0 开边，原有 3 条非流形边没有扩大为本次整身拓扑清理。前后统计分别记录，不将其描述为整只怪物拓扑全面合格。

## 本次实际保存

2026-10-04 后台 commandlet 已完成并正常退出，`import_saved.json` 为 `complete: true`：

- `/Game/Monsters/HangingBellM09/V04/SK_M09`
- `/Game/Monsters/HangingBellM09/V04/Animations/A_M09_Claw`

复用原 Skeleton 和 V13 PhysicsAsset，没有原生代码修改，不需要 DLL 构建。没有打开编辑器或运行游戏。

连续结构预览：`SourceAssets/HangingBellM09Meshy20261003/ArmContinuityV16/Inspection/M09_Claw_Continuous_V16.gif`，颜色用于区分左右小臂，按实际 1.10 秒时序制作，结尾额外停留仅用于观看。
