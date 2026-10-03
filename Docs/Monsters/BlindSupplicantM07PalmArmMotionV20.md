# M-07 V20：掌心朝后、整臂关节与魔法提前量

日期：2026-10-03。工程：`D:/FPS3D/FPSGAME`。

后续状态：用户指出此版移动与参考姿态仍有较大差别。[V21](BlindSupplicantM07FullReferenceGaitV21.md) 已接替慢走／追击及相应速度字段，重新制作完整屈肘与承重姿态；本版的待机、左右横扫、手指解剖定义和原生魔法提前量保留。本文件中的移动参数记录 V20 历史交付，不代表当前移动。

当前阶段：五段动作、FBX 和可编辑源已完成；提前量源码已完成 Game／Editor 两个目标的后台构建。五段独立 UE 动画及现有 AI/F6 蓝图引用已通过无界面 commandlet 实际保存，回执记录 `saved=true`。未启动游戏或测试，观感与命中表现由用户体验。

## 动作范围

用户认可 V19 奔跑姿势有所改善，本次保持该版慢走／追击的双腿、骨盆和胸肩步态，按实际掌心面调整爪子朝向。移动时掌心朝身体后方，关节使用肩、肘、前臂、腕的解剖轴与连续旋转，避免以单独扭手腕达到朝向。

掌心面取腕至中指指根和食指至小指指根的平面，左右镜像显式区分。跑动原肘屈曲为 36–60°，前臂接近水平，不适合只靠旋掌达到朝后；本次保留肩部摆动，将移动肘屈曲调整为 16–28°。共同肘铰链与有界肘平面调整后才添加沿实际前臂方向的旋前／旋后，前臂最多 65°，腕部残余轴向旋转最多 6°，腕横向屈曲最多 25°。目标方向投影至前臂的垂直平面，避免用不可能的朝向折弯手腕；连续四元数与旋转连续性代价用于抑制逐帧翻轴。五指朝实际掌面卷曲，修正右手镜像导致的反向卷指。

横扫继续参考现有百目炉渣使用的 Epic Paragon Rampage `Attack_Biped_Melee_A`，沿用 V18 身体压重、胸肩跟随与安静的非攻击臂。攻击与回收段共同调整，回到与移动／自然下垂一致的手臂姿态；原伤害窗口及近战播放倍率保持。运行时没有独立收势片段，恢复状态暂时保留攻击尾帧，所以横扫尾部和待机手臂必须一致。

历史 V18 攻击臂的入口／末尾接近 T 姿，本次由真实垂臂待机重求攻击臂的起收势，并新增仅修臂掌指的 Idle。左右横扫仍为 1.10／1.20 秒，接触源时间 .47／.50 秒，倍率 1.30，非攻击手随躯干安静保持。现有转场从显示姿态快照开始，无需修改原动画代理或共享 AI。

模型、原 UV、83 骨 V11 参考骨架、V16 手臂权重、V17 腿部权重、V18 显示网格和低成本鳃膜接触／布料继续沿用。此次修改动画，不重新生成或替换原模型。

制作入口：`Tools/BlindSupplicantM07/author_palm_arm_motion_v20.py`。可编辑源、五段 FBX、制作记录和清单保存在 `SourceAssets/BlindSupplicantM07Meshy20261001/PalmArmMotionV20/Motion/`。原蓝图落盘副本保存在 `PalmArmMotionV20/Before/`。

## 魔法瞄准

火球和冰柱按发射手掌位置、发射时的目标位置／速度及实际弹速求交会时间，再朝预测位置发射。求解仅发生在施法接触事件，不新增逐帧预测或追踪弹道。闪电沿用即时射线，在释放接触时取目标位置，不赋予不存在的飞行时长。

原生入口为 `BlindSupplicantCombatMagic.cpp` 的 `M07SpellAim::ProjectileIntercept` 和 `ReleaseMagic`。以 `R = TargetPosition - PalmPosition` 求 `|R + Vt| = Speed × t`，取当前射程内最早的正根；无可达解时直接朝目标发射。弹速沿用火球 1500、冰柱 2000 cm/s，并与执行器相同范围夹限；使用目标完整三维速度。既然采样发生在实际释放接触帧，已经经过的积蓄／推出延迟不再次计入。

预测是恒速估计；目标后续转向、加速或跳跃轨迹变化仍可避开。伤害保持服务端权威执行，预测不改变原魔法执行器的碰撞与复制接口。

保留当前魔攻 40、三元素基础伤害 64／56／60、正式技能 CD 及积蓄／释放时钟。提前量不能绕过遮挡、增加伤害或改变打断退款规则。

## 接入与交付

接入入口：`Tools/BlindSupplicantM07/import_palm_arm_motion_v20.py`。独立动画目录：`/Game/Monsters/BlindSupplicantM07/AnimationsPalmArmV20`；引用保存至现有 `BP_BlindSupplicantM07`，沿用原 AI 与 F6 入口。

最终保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/PalmArmMotionV20/ue_palm_arm_delivery_v20.json`。该回执出现并记录 `saved=true` 才表示资产已实际保存；仅存在脚本不代表已导入。魔法提前量需要原生 Editor 模块构建落盘后才会生效。

本次已实际执行 `run_import_background.ps1` 导入并保存 `A_M07_SlowWalk`、`A_M07_Chase`、`A_M07_SweepLeft`、`A_M07_SweepRight`、`A_M07_Idle` 和 `BP_BlindSupplicantM07`。实际导入日志为 `Saved/Logs/M07Import-20261003-014829.log`。源速度继续为慢走 135／追击 270 cm/s，玩法速度沿用 160／360 cm/s；只替换动画和原角色引用，没有重导模型或追加运行时布料开销。

原生构建已完成，回执为同目录 `native_magic_delivery_v20.json`。实际构建日志为 `Saved/BuildEditor/m07-FPSGAME-20261003-013819.log` 与 `m07-FPSGAMEEditor-20261003-013912.log`，落盘至 `FPSGAME.exe` 与 `UnrealEditor-FPSGAME.dll`。未新增反射字段或运行时预测 Tick。

按用户规则，不主动启动编辑器、游戏、PIE、截图、渲染或测试；由用户从 F6 重新生成后体验。
