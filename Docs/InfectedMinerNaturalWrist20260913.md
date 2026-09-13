# 感染矿工：手腕与前臂姿态修正

2026-09-13。替代上一版拖镐动作中的手部姿态，保留放大 25% 的矿镐、角色模型、骨架绑定、蒙皮、手指抓握和 PBR 材质。

上一版先求肘部位置，再直接旋转持镐手来满足镐尖朝向；前臂转动没有相应配合，导致手腕承担过大的折转。本版从已认可绑定姿态中的中性手腕出发，按镐头高度与骨长重新求可达的肘部和前臂姿态。掌侧方向在整段动画中固定，避免对称镐头引起 180° 翻手；新增前臂转动分布到现有扭转辅助骨，手腕只保留最多 10° 的放松弯曲。

此修改覆盖 Idle、Walk、Attack。左臂局部旋转作平滑处理，攻击首尾衔接拖镐待机；右臂、躯干、腿部以及原有腰部前倾保留。持镐手的路径和镐柄俯仰作了局部调整，不能称为原样动捕。求解使用原镐头最低高度，平滑后不承诺严格逐帧贴地，也未添加坡面 IK。

动画时长仍为 Idle 79/30s、Walk 31/30s、Attack 54/30s。原生 0.16s 状态混合和 22/30–25/30s 伤害窗口保持现状。本轮不修改原生代码。

## 当前资产

- 可编辑源与三动作 FBX：`SourceAssets/InfectedMiner20260913/NaturalWrist/Delivery/`。
- 复用模型：`/Game/Monsters/InfectedMiner/DragGround20260913/SK_InfectedMiner_DragGround`。
- 新动作：`/Game/Monsters/InfectedMiner/NaturalWrist20260913/A_Miner_NaturalWrist_Idle`、`A_Miner_NaturalWrist_Walk`、`A_Miner_NaturalWrist_Attack`。
- 原 `BP_InfectedMiner` 绑定这三个新动作，村庄沿用原刷怪点。

## 制作入口

1. Blender 执行 `Tools/InfectedMiner/relax_wrist_chain.py`，从 `DragGround/Delivery` 生成独立修订版，导出动画 FBX。
2. UE Python 执行 `Tools/InfectedMiner/import_natural_wrist.py`，只导入动画并更新原蓝图引用；保留现有网格、Skeleton、Physics Asset 和材质。
3. 延续用户请求的 GIF：Blender `render_default_preview.py -- --natural-wrist`，随后 Python `package_default_preview.py --natural-wrist`；移动追加 `--state Walk`。输出位于 `NaturalWrist/Previews/`。

动画制作与接入日志分别为 `Saved/InfectedMiner/relax-wrist-chain.log` 和 `Saved/InfectedMiner/import-natural-wrist.log`。GIF/MP4 是离线 Blender 模型预览，不是游戏录像。本轮未进行游戏或回归测试，由用户在村庄测试。商店源资产及派生二进制仅保留本机；Git 发布制作脚本与元数据。
