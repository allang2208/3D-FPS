# 蓄力左臂关节修正 V22

2026-09-14 用户接受格挡 V21，要求按同一方式排查并修复蓄力攻击左臂关节。V22 继承 V21 可编辑源，更新三个同名 UE 动画：`HeavyCharge`、`HeavyRelease`、`Slash1`。保留已接受的 V21 格挡。

用户后续反馈“OK了”，V22 蓄力左臂修正已接受。接下来的装备动画制作入口为 [BackDrawEquipV23](../BackDrawEquipV23/README.md)。

## 关节处理

蓄力抬剑 0.65 秒处，上下臂原旋转基准产生约 155.69° 的轴向差，源网格近景可见肘部拧折。沿用 V21：从前臂变形沿最短摆动建立上臂旋转，同时携带锁骨和两条上臂蒙皮辅助骨，协调肩口与肘部。该指标降到约 71.35°；蓄满处由约 49.12° 降到 14.16°。这些是同一骨架上的诊断指标，不是人体关节角或通用验收阈值。

动态图不能直接全程套用静态格挡修法。快速出剑约 45 ms 经过旋转轴接近反向的区间，直接持续修正会引入新的转动突跳。最终处理是：

- 蓄力起步在 120 ms 内衰减待机姿态的固定残余扭转，避免混入原起步阶段快速翻转的上臂基准。
- 蓄满姿态与重击释放首帧一致；释放前 25 ms 平滑交回原挥砍姿态，不将该算法套入后续快速斩击。
- 未蓄满松手直接跳到 `Slash1` 起势，因此其左臂起势同步采用同一处理，再在 0.65–0.85 秒的原停剑段交回原姿态。普通第一段挥砍也使用此资源。
- 只重建左锁骨、上臂、前臂局部补偿及两条上臂辅助骨的轨道。右手、剑和其他骨骼轨道沿用源曲线；没有修改握点、手指、网格、蒙皮权重或材质。

## 作者源与接入

`author_heavy_arm.py` 读取 `../FistBraceGuardV21/AzureRunesword_Manny_Editable.blend`，并引用 V8 的 `rhythm_clock.py` 以匹配未蓄满松手的时间映射。新 Blend 保留 `REF_V21_` 原动作，三个 480 Hz FBX 位于 `Export/`。

`import_revision.py` 仅导入三项动画，旧 uasset 保存在 `Before/`。上次独立导入因编辑器占用失败；用户要求继续后已通过 `run_import.ps1` 成功保存到原运行目录，见 `import_receipt.json` 和 `import.log`：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_HeavyCharge`：2 秒。
- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_HeavyRelease`：1 秒。
- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1`：1.775 秒。

运行路径无需 C++ 改动或原生重建。已准备的 `import_live_editor.py` / `live_import_client.py` 是编辑器占用时的导入入口，本次成功接入使用独立命令行导入，没有启用远程 Python。

## 用户要求的专项检查

源模型关键姿态见 `Review_FistBraceGuardV21/` 和 `Review_ChargedArmV22/`；对应骨架记录为各目录下 `left_arm_diagnosis.json`。图中开放肩口来自原第一人称手臂网格。

`source_preservation.json` 对三个动作以 960 Hz（含半帧）取 4587 个样本：右手和剑位置差为 0；保留骨骼在原 480 Hz 关键帧上的位置差最大约 0.00053 mm、旋转差最大约 0.000072°，左臂两段长度差最大约 0.00035 mm。重建局部轨道后，帧间左指骨插值最大位置差约 5.02 mm、旋转差约 0.98°，不能称为全部时刻逐位相同。蓄力上臂相邻半帧最大旋转由约 13.13° 降至 4.70°。

`review_in_ue.py` / `run_review.ps1` 已用独立隐藏 UE 进程完成导入后的相关骨骼压缩读回及关键网格姿态检查。以 120 Hz 取 576 个时刻，RAW/COMPRESSED 相关骨骼位置差最大约 0.00583 mm、旋转差最大约 0.0363°；三个时长保持 2、1、1.775 秒。抬剑、蓄满、出剑、回收及未蓄满衔接共保存七张图，其中抬剑与蓄满含左臂近景，肘部形状与源网格一致。回收姿态在第一人称机位已落到屏幕下缘，不把该图当作完整关节近景。结果在 `ue_animation_readback.json`、`ue_review_receipt.json` 和 `UEReview/`；辅助进程已正常退出。

本轮检查限于用户指定的左臂关节及必要动画衔接，没有做完整玩法、伤害、体力、音效或输入回归。最终游戏手感交由用户试玩。
