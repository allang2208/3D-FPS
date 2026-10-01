# 百目炉渣：下劈收势 RampageRecoverV9

2026-10-01。用户明确确认：对象为百目炉渣的大手下劈，非玩家长刀；横扫与下劈攻击主体已认可，仅下劈 recover 手臂扭曲需要重调。

## 修改范围

以实际已保存的 RampageV8 Blender 为基准，复制下劈动作。第 1–32 帧（30 fps，第 1 帧时间为零）原动画键保留；从第 33 帧开始重做收势，第 55 帧仍为原末帧，总时长 1.8 秒。横扫整条动作与下劈伤害窗口 0.84–1.00 秒保持。仅导出与替换下劈，不重新导入网格或横扫。

网格、骨架绑定、骨名、层级、V8 权重、材质、三档 LOD、物理资产与原生战斗逻辑沿用原资产。新增骨骼为零，不需要 C++ 构建。

## 收势修订

V8 的源姿态在 1.55 秒由 GroundSmash_End 直接换成 Idle；整条臂链的待机参考对齐集中在最后 0.25 秒，腕部和扭转辅助骨又根据各自源偏移求解。这些处理可能在几何回撤时叠加扭转；当前判断来自制作源，不是新的游戏画面验收。

V9 使用真实 Epic Rampage `Ability_GroundSmash_End` 的肩臂回撤与肘平面，以上一版第 32 帧的实际姿态为连续起点。完整臂链几何坐标系沿最短四元数弧回到既有待机姿态，保持上臂与前臂固定长度，肘弯曲范围仍为 6–112 度。手腕相对前臂的姿态从既有打击姿态连续回位，由前臂带动手掌，不继续叠加独立的源腕部绕转。

上臂扭转骨、两根前臂扭转骨和主骨共享回位进度；肘腕体积辅助骨按相邻主骨旋转中值更新。掌部仍使用实际网格范围作地面接触修正。末段躯干与其他三条支撑肢按 End-to-Idle 连续混合，不在 1.55 秒突然切换源姿态。

这些属于目标怪物的收势适配；攻击主体和参考来源保持 RampageV8，不把整套动作称作未修改的动捕。

## 制作与保存

当前：Blender 与单条下劈 FBX 已制作，并已导入、保存至原运行资产路径。保存方式为 `existing_editor_bridge`；完成记录见 `RampageRecoverV9/installation_complete.json`。

- 制作源：`SourceAssets/HundredEyedSlagMeshy20260930/RampageRecoverV9/author_recovery.py`、`HundredEyedSlag_RampageRecoverV9.blend`。
- 单条导出：`RampageRecoverV9/Delivery/Animations/A_HundredEyedSlag_AttackSlam_R_RampageRecoverV9.fbx`。
- 原运行路径：`/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSlam_R`。
- 接入脚本：`RampageRecoverV9/install_recovery.py`，原下劈与骨架的恢复副本保存在 `Before/`。
- 记录：`authoring_receipt.json` 为制作记录；`installation_complete.json` 为实际导入保存记录，二者均非视觉验收报告。

接入时主工程编辑器已由用户打开并正在 PIE。首次保存因运行实例占用而退出，未替换资产；按现有流程结束相关 PIE、保留编辑器后，经共享桥互斥完成保存。未主动打开、关闭或重启编辑器，未启动游戏、PIE、渲染或测试。

收势视觉效果由用户体验确认。用户已认可的范围是 V8 横扫和下劈主体，尚未认可 V9 收势。
