# M-07 V14：百目式横扫与三元素蓄力施法

日期：2026-10-02。工程 `D:/FPS3D/FPSGAME`。用户要求将普通攻击替换为参考百目炉渣的横扫，并设计火球、冰柱与闪电，动作参考玩家的积蓄／发射两段。

本轮沿用 `SK_M07_OriginalV13`、原 UV、局部修复权重、低密度布料、三档显示 LOD 与 83 骨 V11 参考帧。只新增战斗动作和执行逻辑，不重新导入身体网格。百目实际横扫的全身蓄勢与肩肘轨迹适配到 M-07 固定骨长，不把百目的非人形骨架直接套到 M-07。

## 行为与默认数值

近身使用左右横扫；中距离、目标可见且相应冷却结束时轮换火球／冰柱／闪电。施法采用积蓄和发射两个独立动作，凝聚效果跟随施法手，只有发射动作的接触时刻提交一次攻击。死亡、控制、打断与目标失效取消尚未发射的法术，阶段结束交回共享 Behavior Tree。

默认魔攻为 **40**，魔法伤害为魔攻乘以下列倍率；实际玩家扣血继续使用现有魔法防御接口，不把基础伤害写成必定扣血。

| 魔法 | 倍率／基础伤害 | 独立冷却 | 设计 |
| --- | --- | --- | --- |
| 火球 | 1.6／64 | 8 s | 飞行火球；范围 14 m、速度 15 m/s，撞击半径 1.4 m，遵循遮挡和同次去重 |
| 冰柱 | 1.4／56 | 10 s | 参考玩家冰锥的单枚长冰柱，凝聚后向前发射；范围 15 m、速度 20 m/s，沿真实飞行路径碰撞 |
| 闪电 | 1.5／60 | 12 s | 手部蓄能后释放一次电弧；范围 12 m，墙面截断，单次命中 |

普通攻击的伤害继续沿用 36；新的横扫动画、接触时刻和实际判定走廊一起接入。魔法不扣玩家蓝量，不改玩家技能成长、施法仲裁或修炼接口。原有奔跑、受击、死亡、导航和 F6 入口沿用。

## 制作与落盘

新增作者目录为 `SourceAssets/BlindSupplicantM07Meshy20261001/CombatMagicV14/`。动作在 `Motion/`，目标资产为 `AnimationsCombatMagicV14/A_M07_SweepLeft`、`A_M07_SweepRight`、`A_M07_MagicGather`、`A_M07_MagicRelease`。实际保存回执为 `ue_combat_magic_delivery_v14.json`。

动作与三元素执行器、共享 AI 接入已完成。四段动作及现有 `BP_BlindSupplicantM07` 已实际后台导入保存（共五个资产），原生默认引用已指向保存后的四个动作，必要 Editor／Game 构建均已完成。保存回执 `ue_combat_magic_delivery_v14.json` 记录 `saved=true`；构建成功不表示运行验收。

本轮生产日志：`Saved/Logs/M07Import-20261002-185530.log`。为实际导入所需的新反射模块构建为 `Saved/BuildEditor/m07-FPSGAMEEditor-20261002-185206.log`；最终编辑器构建为 `m07-FPSGAMEEditor-20261002-185629.log`，最终游戏构建为 `m07-FPSGAME-20261002-185659.log`。没有重新导入模型、物理资产、布料或导航。

四段动作由 `Tools/BlindSupplicantM07/author_sweep_cast_v14.py` 制作，保留可编辑 `Motion/M07_Original_SweepCasting_V14.blend` 与四个 FBX。实际参考为百目当前 `AttackSweep_R`、`RampageV8/author_rampage.py` 与 `Attack_Biped_Melee_A.json`；玩家动作参考为当前 `FireballCastMotion.h`、`FPSFireballComponent.cpp`、`FPSCastingMeshComponent.cpp` 与版本 6 的 `fireball_hand_pose.json`。

左右横扫时长分别为 1.50／1.667 秒，接触中心为 0.68／0.78 秒，判定窗口为中心前后各 0.08 秒。积蓄时长 1.10 秒，发射时长 0.80 秒，发射段 0.30 秒提交魔法，总起手到提交为 1.40 秒。两段动画用继承的唯一 `StateTime` 连续采样。

`BlindSupplicantCombatMagic.cpp` 负责选择、冷却、积蓄取消和接触，`M07MagicAttack.cpp` 执行元素命中与表现。共享 `NurseZombie` 只增加可覆盖的时长／接触钩子及虚打断接口，默认护士行为保留。近身横扫沿中指末节的实际轨迹球扫，并参考百目的手爪前向延展方式；实际攻击距离沿用全局 1.5 倍规则。各魔法在释放提交时开始独立冷却，前摇被打断不消耗该招冷却。

瞄准在积蓄阶段随存活目标更新，进入发射段时锁定，释放点在接触帧从左手掌骨采样。已发射火球／冰柱不追踪玩家；死亡／销毁会取消尚未命中的弹体。伤害来源保持为 M-07，三种元素分别走 `UFireballDamage`／`UIceSpikeDamage`／`ULightningDamage` 与玩家魔防、格挡和远程闪避接口。

本轮按用户规则后台制作、必要编译与保存，不主动打开 UE、PIE、游戏，不截图、渲染或追加测试。最终由用户从 F6 重新生成 M-07 测试动作、魔法和数值。
