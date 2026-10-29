# 弯刀第三段突刺：原始左臂动作迁移

2026-10-25。用户否定 ThrustWristV5 的自然度后，改用本地 KayKit `Melee_1H_Attack_Stab` 的完整左臂动作，制作 Jason、Kaitlin 的 ThrustSourceArmV6。V5 的腕部角度修正没有解决整臂表演，不能作为已认可版本。

## 来源与动作处理

原始来源为 KayKit Character Animations 1.1（CC0），本地源文件位于 `SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/Animations/gltf/Rig_Medium/Rig_Medium_CombatMelee.glb`。本轮读取原始 UE Donor：`/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Donors/KayKit/SK_KayKit_Medium_Anim_Melee_1H_Attack_Stab`，不使用旧版剑动作的重定向缓存。

这条 1.6 秒动作的左臂随突刺向侧后方回收、配合发力，再逐渐回位。V6 迁移其肩关节（upperarm）、肘关节（lowerarm）及掌部（hand）的连续旋转，保留这种整体配合，不沿用 V5 手臂固定抬至护拳位置的轨迹。

- 在胸部相对空间适配原生骨架，保持各身体实际骨长。源角色的根位移和躯干倾斜不会再次叠加到现有身体上。
- 源动作右腕相对肩的前伸峰值位于约 0.4333 秒，对齐现有突刺 0.367 秒接触时刻；左臂全部关节共用一条分段时间映射。
- KayKit 存在独立的 wrist 和 hand 节点，按真实前臂末端和掌向匹配，不把手掌内部位置当作玩家腕点。
- 保留原来的握拳手指。源动作蓄势期的较大屈腕经连续的柔性限幅适配闭拳，保留原掌部时序和轴向运动；重算原生左前臂扭转辅助骨。
- 从第二刀的实际终姿接入，在前 0.24 秒逐渐转入源左臂表演；0.76 秒后逐渐回到原待机，首尾保持原姿态。

只修改左上臂、前臂、手掌和两根前臂扭转辅助骨的旋转。保留右手刀路、躯干、双腿、手指握拳曲线、接触及释放时刻。

## 制作入口

`SourceAssets/KukriThrustSourceArm20261025` 保存：

- `prepare.py`、`kaykit-stab-source.json`：原始 Donor 和本轮实际使用的突刺资产输入。
- `author.py`、两套 `*-actions.json`、`authoring.json`：可重建的原生动作和时间映射。
- `save_assets.py`、`run_commandlet.ps1`：通过既有批次互斥在后台保存新动画包。
- `publish.py`：使用共享配置事务，仅更新两个 `Kukri.FullBody.Thrust` 字段。

新动画路径：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason|Kaitlin>/Animations/ThrustSourceArmV6/A_KukriCombo_ThrustSourceArm`。沿用现有 Cook 目录、`Contact`、`Release` 和 `NativeSwordGrip` 标记。旧版本及其制作源保留。

本轮没有改动 C++，无需原生编译。保存和本地配置接入结果记录在 `assets-saved.json`、`published.json`、`delivery.json`；未运行游戏、渲染或进行观感验收。配置在角色 `BeginPlay` 读取，已有游玩需结束并重新进入才能加载新入口，不需要为本轮资产修订重启编辑器。
