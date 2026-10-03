# M-07 V34：完整背膜统一驱动与末端轻摆

2026-10-03。用户要求完成 V33 回退后新方案的接入。V31 曾因破碎和扭曲加重被否定，本轮从已回退的 V18 原显示网格继续制作。

## 实现

完整显示面直接使用原有连续蒙皮、83 骨参考和六片背膜骨链，移除旧的显示面到碎片布料代理映射。原几何、厚度、轮廓、UV、材质、根部连接和蒙皮权重保持原值。新实现采用统一骨骼驱动，而非另造一个仍需逐顶点回退的布料捕获代理。

每片组织根部随原身体动画。中部和末端在共同弯曲平面内分担轻微摆动，固定骨长，保留原动作姿态；不引入绕组织纵轴的扭转。响应根部转动与角色加减速，使用解析临界阻尼弹簧，避免普通逐帧欧拉累积。上层最大附加弯曲 1.8°，其余 1.3°，中部／末端按 25%／75% 分担；待机呼吸仅 0.18°。

现有手臂避让仍在二次摆动后执行，额外开合上限降至 4°；已烘焙的臂部走廊和身体联动保持原值。死亡及击倒由既有动作／物理接管，附加摆动停用。

## 性能范围

- 六个受限角度弹簧、十二根自由段骨骼，接入原动画图，不新增 Tick、射线或 IK。
- 移除本角色背膜的粒子布料与显示捕获，不再强制锁定近距 LOD0；沿用现有距离 LOD。
- 二次摆动只用于 LOD0／LOD1；远处保留原骨骼动画。
- 未测量帧率，不将减少求解工作量表述为已测 FPS 收益。

## 接入与恢复

正式显示资产仍为 `/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18`，原 AI/F6 蓝图启用 `bUseCoherentGillMotion`。V25 移动、V32 攻击、V30 悬浮施法、V29 死亡和 V33 过渡支撑修复保留。

接入前原网格和蓝图备份至 `SourceAssets/BlindSupplicantM07Meshy20261001/CoherentMembraneV34/Before`；不覆盖 V33 回退凭据和 V31 前备份。制作源为现有 `BodyMotionV18/Proxy/M07_Original_GillContacts_V18.blend` 和本轮运行节点，不需要重新导入相同几何 FBX。

原生源码：`Source/FPSGAME/Monsters/M07MembraneMotionNode.h/.cpp`，以及当前 M07 AnimInstance／Monster 中的节点和模式接入。保存脚本：`Tools/BlindSupplicantM07/import_coherent_membrane_v34.py`。

Game 必要构建完成：`Saved/BuildEditor/m07-FPSGAME-20261003-202846.log`。Editor 必要构建完成：`Saved/BuildEditor/m07-FPSGAMEEditor-20261003-203744.log`。

原网格及原 AI/F6 蓝图现已实际保存：`SourceAssets/BlindSupplicantM07Meshy20261001/CoherentMembraneV34/ue_coherent_membrane_delivery_v34.json`，`saved: true`、`coherent_motion_enabled: true`、`actual_cloth_asset_count: 0`。编辑器批次桥保存记录为 `Saved/Logs/M07-V34-EditorSave-2050.txt`。

两次后台保存期间均出现新启动的交互编辑器占用网格（Error 32），未覆盖资产；第一次转桥时 PIE 门控也在修改前停止。最终通过当时已打开的编辑器、同一批次互斥完成保存，没有主动打开编辑器或终止其他进程。

本轮不主动启动编辑器、游戏、预览或渲染，未做自动验收，由用户体验。
