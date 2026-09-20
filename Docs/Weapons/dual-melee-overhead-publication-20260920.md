# 双持快速近战与双手冲刺下砍：发布和恢复

2026-09-20，按用户要求整理本任务废案、沉淀 SKILL 并发布源码。当前工程为 `D:/FPS3D/FPSGAME`，目标为 `allang2208/3D-FPS` 的 `main`。本次不开展新游戏测试或动作验收。

## 当前接入

| 范围 | 当前源／运行资源 | 状态 |
| --- | --- | --- |
| 双持 M1911／DW715 | `SourceAssets/DualPistolQuickCombat20260920/SpinRecoveryV5`；`/Game/Weapons/DualPistolQuickCombat20260920/SpinRecoveryV5` | 36 条动画已保存，当前运行源码按每只手装配选择 compact／fitted／long；0.80 s、0.18 s 单次接触。候选尚待实机观感确认。 |
| 标准柄冲刺下砍 | `SourceAssets/RuneSwordDowncutReach20260920/Standard`；`/Game/Weapons/AzureRunesword20260913/A_RuneSword_Overhead` | 已安装 V5。 |
| 长柄冲刺下砍 | 同上 `LongGrip`；`/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Overhead` | 已安装 V5。 |
| 待机／其他剑动作 | `SourceAssets/RuneSwordWristLocked20260920` | V4 腕肘支撑仍有效；两条 Overhead 由 V5 最后覆盖。 |
| 竖直空间扰动与冲击 | `RuneSwordPickaxeOverhead20260920/ImpactV2`；`SprintOverhead20260920/SM_RuneRift_Overhead`；`RuneSwordOverheadFeel.h` | 沿用 V2 的 80 ms 落点停顿、竖直扰动、音效与镜头。 |

双持沿用 F 触发修复、左右出手轮换和一击一结算。双手剑保持 2.60 s、1.22–1.40 s 命中窗，V5 将完整下砍段展开，保留手腕朝向和剑局部握姿；没有缩放模型或拉长骨骼。

**DW715 枪身／弹巢形变反馈未解决。** `SpinRecoveryV5/RigidFix` 是诊断目录，名称不代表已经修复。此前采样未发现枪体骨缩放／相对漂移，读取时没有问题运行帧；仍需围绕用户观察继续定位，不把它记录为已通过。

## 废案归档

本机归档根为 `trash/dual-melee-overhead-retired-20260920/`，逐文件恢复清单为 [归档清单](../Rejected/dual-melee-overhead-retired-20260920.json)，记录原路径、目的路径、大小、SHA256、原因和替代物。

- 退役双持 V1／FlowV2 源产物、取消改造枪转枪的 AttachmentClearanceV4 及旧包。编辑器读取的 18 个旧包没有引用者或未保存修改，先保存校验副本，再经编辑器资产 API 移出；当前 V5 与 V3 对照资产保留。
- 退役双手剑首轮十字镐移植产物、被否定的 ElbowRepair V3 解算与输出，以及各轮覆盖前快照。没有归档仍用于制作的 ImpactV2 标定源或 V4 对照 Blend。
- 不改其他任务文件，不全库清理。恢复旧资产前需明确版本，不能把整份 C++ 快照覆盖回共享工程。

## 必须保留的作者依赖

1. 双持 V5：`PistolDualWield20260914/NaturalAimV3` 四套合法本地 Blend → `SpinRecoveryV5/prepare_author_geometry.py` → `author_actions.py -- M1911|DW715` → `import_assets.py`。V5 仍读取 VideoRefV3 的纯函数与手工 `motion.json`；根目录共享导入器仍供 V3 对照导入使用。
2. 双手剑：`RuneSword20260913/ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend`、`PickaxeSightline20260919/author_attack.py` 与 `motion.json` → ImpactV2 `author_overhead.py`／`author_rift.py`。保留 ImpactV2 标准柄 Blend 与 `authoring.json` 中的 `skin_stations`。
3. V4：`RuneSwordElbowRepair20260920/Standard_active.json`／`LongGrip_active.json` 是 V3 修改前的合法本地密集快照。五个换轴／邻域函数已原样提取至该目录 `pose_conversion.py`，V4／V5 已改读此文件；V3 作者脚本可安全退役。该目录原 `import_receipt.json` 仍供 V4 目标捕获脚本使用。
4. V5：保留自己的 `Standard_input.json`／`LongGrip_input.json`、`reach_solver.py` 和两套完整 Blend／FBX。恢复时先 V4 后 V5，最后运行 V4 安装会覆盖新版 Overhead；安装器的目标散列保护应保留。完整源恢复与重新采样是前置条件，不能仅克隆公开仓库就假定可重建所有动作。

## 公开边界与检查

只发布本任务 C++ 片段、作者／导入／定向诊断脚本、手工动作参数、说明、归档哈希清单和 SKILL。第三方枪械／Manny／近战模型及其 Blend、FBX、uasset、纹理、完整骨骼采样、用户参考视频、缓存和 trash 内容继续保留本机。Bilibili 仅用于动作观察，没有提取其游戏资产，也不将视频作为可再分发文件。

本次只做用户要求的仓库整理和推送检查：归档路径／哈希／旧包引用，暂存范围／差异／大小／敏感信息／许可边界，以及远端提交范围。此前必要 Live Coding／Editor 构建和定向姿态检查记录见各版 README；此次没有新编译、PIE、自测、渲染或游戏回归。`QuickCombatState` 历史排队没有完成结果，不记为通过。

经验入口：[双持快速近战](../../skills/ue5-fps-arms-animation/references/dual-pistol-quick-melee.md)、[过顶下砍伸展](../../skills/ue5-fps-arms-animation/references/overhead-reach-wrist.md)，个人 SKILL 与仓库镜像同步。
