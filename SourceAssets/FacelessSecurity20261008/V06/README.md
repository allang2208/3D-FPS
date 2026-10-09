# 无面安保 V06：连续肩袖、贴身腰带与恢复衔接

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

2026-10-08。用户提供 V05 游戏截图，指出移动时肩膀与两臂连接异常、腰侧仍有细小悬空件，以及攻击后恢复不自然。V05 未获用户认可，本版继续修改原安保入口。

后续用户指出腰侧黑块仍存在。[V07](../V07/README.md) 已定位到裤子网格内部的两块独立残片并移除；本版删除腰带附件的操作没有覆盖实际问题来源。当前正式网格使用 V07，动作仍使用本版。

## 肩袖与腰部

- V05 的衣身和袖筒是互相重叠的独立表面；衣身随脊柱运动，袖根随手臂运动，抬臂后会分开。本版删除独立衣身／袖筒，取回 V04 由身体表面生成的连续衬衫拓扑，完全丢弃其旧蒙皮权重。
- 沿衣物相连的网格边计算肩窝过渡，躯干、左臂、右臂分别设置固定权重区域。前臂与腰部即使在制作姿势中相距很近，也不跨空隙交换权重。肩根连续过渡到同侧锁骨和上臂，袖筒继续跟随同侧肘腕。
- 删除腰侧独立袢带、旧袖扣和原腰扣零件，重建紧贴裤腰的连续皮带与前方腰扣；皮带按裤装表面取样位置和权重。胸袋、肩章、领片与其余小件重新贴合衣物，小硬件使用同一附着锚点。
- 保留完整手指、双脚、鞋靴、V05 裤装和完整身体母版。本版没有改动材质或女接待员。

## 恢复动作

原 V03 攻击结尾收回到弓背 Idle_A，V05 移动换成抬臂 Walk_B 后，退出攻击会直接切换到另一种上身姿势；原控制器还会在攻击末帧停留 0.38 秒。

- Walk_B 保留原循环内容、时长和速度，仅将循环起点移至原第 117 帧附近的支撑姿势。用这一姿势统一恢复末帧、待机首帧和移动首帧。
- 待机把原 Idle_A 的轻微上身变化叠加到新的抬臂准备姿势，腿部保留支撑位置。
- 保留攻击 0.20–1.10 秒的挥击主体和原命中窗口。之后采用原生 Attack_D 的收势轨迹，逐渐回到统一准备姿势；同一条手臂的肩、肘、腕、手指使用同一条恢复曲线，避免末段手腕单独拖后。
- 攻击片段由 2.30 秒延长为 2.566667 秒，将一部分原静止恢复时间用于连续收势；末帧恢复等待由 0.38 秒缩为 0.113333 秒。整轮攻击加恢复仍为 2.68 秒，命中窗口仍约 0.589565–0.785882 秒。
- 按现有鞋底表面保持烘焙接地，网格相对 Z 继续为 -94.15 cm；移动速度 78 cm/s、Walk_B 资产倍率 0.499256 保持原值。

本次通过动画资产匹配端点，不新增运行时动画混合器或地形 IK。

## 实际交付

三个骨骼网格、三段动作与原蓝图已在现有 UE 编辑器中通过互斥桥实际导入、保存，`ue_delivery.json` 为 `stage: saved`，桥返回 `success=True`。

- `/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_V06`
- `/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Clothing_V06`
- `/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Body_V06`
- `/Game/Monsters/FacelessSecurity/Animations/V06/A_Security_Male_V06_idle`
- `/Game/Monsters/FacelessSecurity/Animations/V06/A_Security_Male_V06_walk`
- `/Game/Monsters/FacelessSecurity/Animations/V06/A_Security_Male_V06_attack`
- `/Game/Monsters/FacelessSecurity/BP_FacelessSecurity`，F6 名称仍为“无面安保”。

穿衣组合 192586 三角面，完整身体 199401 三角面；161 骨、7 材质槽，59 个独立衣物对象。Blender 制作源在 `Authoring/`，动作源在 `Motion/`，三种模型的 FBX／GLB 在 `Delivery/`。旧版本保留。

制作脚本为 `Tools/FacelessSecurity/sew_shoulders_v06.py`、`author_recovery_v06.py`、`import_security_v06.py`；数据记录为 `shoulder_rebuild.json`、`export_receipt.json`、`motion_manifest.json` 和 `ue_delivery.json`。导入记录为 `Logs/import_bridge_02.txt`。

为接入资产结束了用户当前 PIE，未关闭或重启现有编辑器，没有主动启动游戏、渲染、测试或验收。本版无 C++ 修改。以上是制作与保存记录，游戏中的肩袖、腰侧和收势表现由用户测试。
