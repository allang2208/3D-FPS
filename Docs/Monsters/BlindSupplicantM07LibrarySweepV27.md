# M-07 V27：复用动作库完整挥击

日期：2026-10-03。用户否定 V26 横扫：手臂穿入身体、整臂扭曲、打击感弱，要求在动作库中直接选用合适挥击。

## 连续恢复修订

用户认可下陷修复后的攻击主体，继续反馈恢复阶段有僵硬停顿。排查显示旧制作在约 1.2 秒进入源动作的近静止尾段，至 1.7 秒才开始全身同步回待机，回收被压缩在最后 0.3 秒。恢复期攻击手角速度峰值为左 846.80／右 637.47 度每秒。

当前 `V27ContinuousRecovery` 保留 0–1.0 秒逐骨姿态，1.0 秒后骨盆／身体先回正，脊柱、肩臂、腕部按小幅延迟连续收回，2.0 秒接到原待机。使用五次平滑权重，并只平滑恢复段肩部整体避让曲线；不改供体挥击、命中、总时长或冷却。接地沿用前次修复，无新增运行时 IK、Tick 或 C++ 变更。

本次按用户“排查并修复”范围进行了离线逐帧曲线诊断：左右 0–1 秒的全部骨矩阵最大差为 0；攻击手恢复角速度峰值降到左 290.04／右 247.42 度每秒，骨盆恢复角速度峰值从约 142 降至约 43 度每秒。原 1.3–1.6 秒近静止区间已改为持续收势。这些数值说明曲线变更，不替代游戏观感验收。

诊断记录位于 `LibrarySweepV27/RecoveryFix/before_curves.json` 与 `after_curves.json`，脚本为 `Tools/BlindSupplicantM07/diagnose_recovery_v27.py`；已认可片段的制作约束保存在 `RecoveryFix/accepted_motion_manifest_v27.json`，源文件和资产备份位于 `RecoveryFix/Before-20261003-171053/`。左右正式动画、现有 AI/F6 蓝图、可编辑源与 FBX 均已保存，回执 `ue_library_sweep_delivery_v27.json` 的 `recovery_revision=V27ContinuousRecovery`、`saved=true`；后台生产日志为 `Saved/Logs/M07Import-20261003-171743.log`。最初连接时编辑器已自行关闭，随后完成无界面导入，没有重开编辑器、启动游戏或新渲染，恢复效果由用户试玩。

## V27 攻击下陷修订

用户随后反馈攻击时陷入地下。制作输入中，参考骨盆高度为 133.32 cm，但原生重定向动作的 pelvis 高度接近 0；默认 Root Motion Generator 将 Manny 的地面根骨写到 M07 唯一的骨盆根骨，同时覆盖了骨盆旋转。离线重建固定骨长时沿用了该错误根变换，使全身下陷。

本次禁用该地面根运动复制操作，保留原生 Pelvis 重定向，重新生成完整原生姿态输入。离线制作按参考骨盆原点注册位移，使用实际显示网格中脚／趾蒙皮顶点，将每帧最低支撑面匹配到当前待机脚底；只烘焙整体竖直位移，不修改四肢相对旋转，不以手爪或背膜最低点决定接地。源动作踏步、沉身、转体和左右攻击的 2 秒／0.60 秒接触合同保留。

动画导入显式关闭根运动提取及强制根锁，避免作为根骨的 pelvis 再被固定。修订标记为 `V27PelvisGroundingFix`，仍使用现有两段 V27 正式资产路径。备份位于 `LibrarySweepV27/GroundingFix/Before-20261003-164718/`。原生重定向、可编辑源、左右 FBX、左右正式动画与现有蓝图均已后台保存；当前回执为 `ue_library_sweep_delivery_v27.json`，生产日志 `Saved/Logs/M07Import-20261003-164905.log`。没有新增运行时处理、修改角色胶囊或地图地面。未测试，交由用户试玩。

## 选源

本地 `ZombieAnimationPack` 已有 UE4／UE5 两套动作。读取现有库清单与源动作分帧后选择 UE5 `anim_Attack_D`：抬臂蓄势、踏步转体、快速斜向挥抓和站立收势。Attack A/C 有前扑落地，Attack B 侧转较多，不采用。当前源图位于 `SourceAssets/SpitterZombieMeshy20260927/LibraryReview20260928/Preview/Attack_Early_Phases.png`；本轮只读取已有图，没有新渲染。

源资产：`/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D`。源模型：包内 `SK_Manny_Simple`。已有本机素材复用；不公开分发原素材包、FBX 或密集姿态。

## 制作方法

通过原生 IK Rig／IK Retargeter 输出干净完整动作，身体、肩、肘、腕、踏步和收势共同迁移。四肢采用 `OneToOne` 对应关节复制，避免不同长短比例下的长度归一插值影响肘部旋转。V25/V26 的手掌目标、肘平面限幅与前臂旋转解算不再用于新横扫。

离线适配保持原生输出的肘、前臂与手腕相对旋转，从肩部整体调整一条手臂及长爪的避让姿势；用原身体蒙皮范围制作躯干包络，包含前臂、掌和长指厚度，整段动作同时考虑连续性。该过程不分别追手掌目标或扭转前臂。保留原爪型并接回当前待机；另一侧攻击由完整源动作镜像得到。

保留源动作 2.00 秒节奏，按 60 Hz 烘焙。命中中心 0.60 秒，窗口 0.20 秒（0.50–0.70 秒），播放倍率 1.0。身体重心、踏步、击打与收势取自同一段动作；现有战斗时钟同步更新，不靠特效或镜头改动代替动作。

组织避让继续烘焙并沿用已有运行时预算；本轮不新增运行时 IK、全网格碰撞或新的 Tick。

## 文件与状态

- 原生重定向：`Tools/BlindSupplicantM07/retarget_library_sweep_v27.py`
- 原生姿态制作输入：`Tools/BlindSupplicantM07/cache_library_retarget_v27.py`
- 体型适配与导出：`Tools/BlindSupplicantM07/author_library_sweep_v27.py`
- 最终导入：`Tools/BlindSupplicantM07/import_library_sweep_v27.py`
- 制作根：`SourceAssets/BlindSupplicantM07Meshy20261001/LibrarySweepV27/`
- 原生保存记录：`native_retarget_v27.json`
- 正式动画目录：`/Game/Monsters/BlindSupplicantM07/AnimationsLibrarySweepV27`

干净原生重定向、可编辑 Blender 源、左右 FBX、两段正式 UE 动画和现有 AI/F6 蓝图均已实际保存。当前回执：`LibrarySweepV27/ue_library_sweep_delivery_v27.json`；下陷修订导入日志：`Saved/Logs/M07Import-20261003-164905.log`（初版日志为 `M07Import-20261003-163050.log`）。实际资产时长均为 2.00 秒，左右命中中心 0.60 秒，窗口 0.20 秒。

原生姿态采用 UE 直接采样的厘米制变换，显式保留作为根骨的 pelvis，避免动画 FBX 导入 Blender 时把 pelvis 转为 Armature 对象而漏掉根骨。中央躯干包络仅取 `M07_OriginalBody_Display`，排除高模副本、碰撞代理和外侧／背侧组织，最终半径为横向 25.28 cm、前后 21.41 cm；掌爪厚度另计，组织由已有独立采样层处理。这些为本模型制作输入，不作为其他怪物默认尺寸或无穿模保证。

V25 移动、V24 施法及模型、蒙皮保持当前版本。没有修改 C++、新增运行时 IK 或重新打开编辑器。未测试或新渲染，视觉质量与打击感由用户体验确认。
