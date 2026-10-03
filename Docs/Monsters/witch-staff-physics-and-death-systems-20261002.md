# 巫婆法杖物理掉落与倒地、死亡逻辑梳理

**2026-10-03 更正：** 本页记录上轮制作状态。进一步读取碰撞发现八个凸包全部位于骷髅，杖身未覆盖；仅凸包数量不能证明碰撞完整。死亡物理准入顺序、法杖释放时机与死后修姿也已继续修改，当前处理见 [巫婆尸体与法杖物理交接修复](witch-physical-settle-20261003.md)。

用户反馈：尸体仍僵硬，法杖竖立在地上；要求死亡后自然掉落，并排查布娃娃以外的倒地、死亡规则。按源码职责分类计数，不按文件数量计数。本次仅做所需源码排查、制作、资产保存和普通构建，不启动游戏、PIE、渲染或自动测试。

## 本轮调整

- 原法杖 `WitchStaff` 在死亡后仍绑定 `hand_l`，碰撞为 `NoCollision`，没有独立模拟。这是截图竖杖的直接代码原因。
- `AWitchMonster::ReleaseStaffOnDeath()` 在换尸体网格前松手。普通死亡、物理击飞中死亡、倒地或起身中死亡都经过这一入口；重复调用只处理一次。
- 已在物理中时从左手刚体取得位置、线速度和角速度；动画状态采用连续两帧的法杖运动。释放保持世界姿态，继承质量中心速度，不指定落地角度、不施加虚构挥飞冲量。
- 新专用资产 `/Game/Monsters/WitchRebuilt/Props/SM_WitchRebuilt_StaffPhysics` 复制原法杖外形、尺寸与材质，增加沿弯曲杖身及骷髅的多凸包碰撞。未改旧共享外观资产。专用物理材质 `PM_WitchRebuilt_Staff` 摩擦 0.65、弹性 0.08；运行时质量 2.5 kg、线性阻尼 0.05、角阻尼 0.15，开启重力和 CCD。
- 法杖释放后属于独立物理组件，尸体定姿不冻结它；随原尸体生命周期一起清理。物理道具阻挡世界和物理物体，忽略 Pawn 通道。
- 巫婆死亡专用肩、肘、腕关节活动范围放宽，让施法姿态能由重力继续松落；关节锚点、线性锁定和连体身体保留。肩 95/75/60 度，肘 105/12/20 度，腕 35/30/25 度。活体击倒、起身及其他怪物不采用这些死亡专用范围。

## 布娃娃以外的 7 组相关逻辑

| 编号 | 系统职责 | 当前实际影响与边界 | 主要源码 |
| --- | --- | --- | --- |
| 1 | 生命、死亡状态与尸体生命周期 | 伤害结算后生命归零才进入 `Dead`；禁止后续攻击、关闭移动和角色胶囊；优先接续已有击倒状态；默认尸体存留 15 秒后销毁。 | `NurseZombie.cpp::TakeDamage` |
| 2 | 战斗控制、破韧与状态异常 | 破韧/眩晕选择受击表现，冻结/石化采样固定受击姿态；技能击飞经 `ReceiveKnockdown` 进入倒地。成功击飞清除站立眩晕和推挤计时；倒地时后续控制延长倒地时间，死亡后的普通受击/眩晕表现不再驱动。枪械原有无硬直设置保留。 | `MonsterCombatComponent.cpp`、`MonsterMeleeKnockback.cpp`、`MonsterStunPresentation.cpp`、`CombatStatusFormula.cpp` |
| 3 | AI、导航、角色移动与胶囊 | 死亡停止行为树和寻路；角色胶囊、移动模式负责活体落体回退与起身空间。起身须找到可走地面并容纳站立胶囊，不能只按动画时间强行站立。巫婆自身施法朝向只在 Idle/Chase 更新。 | `MonsterAIController.cpp`、`NurseZombie.cpp`、`WitchMonster.cpp`、`HumanoidKnockdownComponent.cpp::TryGetUp` |
| 4 | 动画播放器、死亡交接与起身 IK | 普通死亡先播 `DeathBackward`，约 60% 交给物理；已处在倒地链中的死亡直接延续当前姿势。活体起身仍用仰卧/俯卧标准动画和姿势快照混合。行走足锁在倒地/起身时关闭；起身专用腿部防裙摆穿模和支撑高度修正仍会改最终动画姿态。死亡切为基础快照播放器，不继续巫婆行走/起身 IK。 | `WitchMonster.cpp::StartDeathPresentation/StartRagdoll`、`FatZombieAnimInstance.cpp`、`WitchRebuiltAnimInstance.cpp`、`WitchRecoveryLegNode.cpp` |
| 5 | 连体尸体网格与布料显示 | 倒地、起身及死亡改用连体裙身、完整腿皮的 CorpseFollow 网格；独立布料模拟在这一期间暂停。活体恢复站立才切回原网格并重置、渐入布料。尸体裙摆目前随骨骼变形，其硬度不会因法杖增加刚体而消失。 | `WitchRebuiltMonster.cpp::UseCorpsePresentation/UseKnockdownPresentation/RestoreStandingPresentation/Tick` |
| 6 | 物理结束后的可见表面接地修正 | 停止布娃娃后，基于可见网格采样修正整尸高度、胸背、头部和脚部；手只纠正穿地，不强迫放低。此模块会改变已模拟出来的姿态，是可能产生人工定姿感的来源。它不负责连续刚体运动，已释放法杖不参与该修正。 | `WitchCorpsePose.cpp::GroundCorpsePose`、`HumanoidKnockdownComponent.cpp::StopPhysicsWithPose` |
| 7 | 持械道具挂接 | 活体 Staff/Bottle 跟随手骨；旧版死亡仍保留法杖挂接，手姿态冻结就导致竖杖。本轮法杖死亡脱离并模拟，瓶子继续原手骨跟随。 | `WitchRebuiltMonster.cpp::AttachProps`、`WitchMonster.cpp::ReleaseStaffOnDeath` |

上述模块中的起身许可、碰撞交接函数由倒地组件编排；此表按它们依赖的系统职责分类，没有把它们误算成 7 个独立布娃娃。

## 布娃娃内部仍会影响僵硬感的规则

`MonsterRagdollPhysics` / `UHumanoidKnockdownComponent` 和 `UHumanoidRagdollBudget` 属于同一布娃娃流程，不加入上表计数：

- 物理资产的碰撞形状、关节锚点与角度限制，以及运行时质量/阻尼/约束驱动，决定身体是否能自然下落。死亡巫婆已关闭角姿态和角速度驱动；本轮只放宽其死后手臂范围。
- 默认预算为 8 个角色、128 个刚体、最多 4 个新尸体准入；不足时走动画倒地回退。活体控制可以释放已稳定尸体的预算，因此不同场景的尸体不一定保持同样长的动态模拟。
- 巫婆尸体物理至少 2 秒，要求接地且全身低速累计超过 0.65 秒后可定姿。低速定义由 `MonsterRagdollPhysics::IsSettled(Mesh,20.f,.5f)` 给出。
- 定姿将刚体转成快照、停止身体物理及网格 tick，并执行上表第 6 项接地修正。之后尸体不会继续物理晃动；独立法杖继续由 Chaos 决定自然睡眠。

## 已排除的活体叠加表现

- `MonsterIdleBreathingMeshComponent`：死亡、受控、倒地或物理模拟时关闭待机呼吸，未发现其继续顶住尸体。
- `MonsterGunHitFeedback`：同样在死亡、受控、倒地、物理模拟时关闭并清空脉冲，未发现枪击轻反馈重新摆正尸体。

这是当前源码路径的排查结论，不是运行验证结论。本轮不移植多人布娃娃复制、不替换标准起身动作、不恢复会拆开脚部的旧尸体组件。

## 落盘状态

制作脚本：`SourceAssets/WitchStaffDrop20261002/prepare_staff_physics.py`。
后台执行与普通构建：`SourceAssets/WitchStaffDrop20261002/Complete-Background.ps1`。
实际落盘完成：法杖网格和物理材质已保存，生成 8 个凸包；Game 与 Editor 常规构建均完成。

- Game：`Saved/BuildGame/witch-staff-drop-20261002-235140.log`，Succeeded，27.17 秒。
- Editor：`Saved/BuildEditor/build-20261002-235208.log`，Succeeded，31.32 秒，普通基础模块构建。
- 保存与构建收据：`SourceAssets/WitchStaffDrop20261002/Receipts/assets.json`、`Receipts/delivery.json`。

首轮静态网格编辑器子系统在 commandlet 中不可用，未完成碰撞保存；改用 GeometryScript 源网格读取、凸包生成和静态网格碰撞写入后完成保存，失败日志保留在 `Receipts/attempt1-*`。没有打开交互编辑器或游戏。未进行运行或视觉测试，由用户自行测试。
