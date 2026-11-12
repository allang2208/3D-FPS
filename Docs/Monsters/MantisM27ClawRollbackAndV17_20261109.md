# 螳螂普通攻击回退与旧版局部调整

2026-11-09。用户反馈普通攻击仍别扭，要求先恢复修改前版本，再在原版本上调整。

## 已恢复的正式版本

根据 `SourceAssets/MantisM27/Beast06V2/activation_receipt.json` 中正式蓝图的 `previous` 字段，本轮 Beast06 普攻接入之前使用的是 **ClawV16**。本次据此恢复原资产引用，而非根据版本号猜测回退目标。

以下三个蓝图的 `attack_clip`、`left_slash_clip`、`right_slash_clip` 已恢复 ClawV16 并保存：

- `/Game/Monsters/MantisM27/BP_MantisM27`
- `/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1`
- `/Game/Monsters/MantisM27/ArmChainV15/BP_MantisM27_ArmChainReviewV15`

正式 F6 螳螂现在为 **ClawV16 普攻 + PounceV11 飞扑**。ArmChainV15 对比角色的飞扑候选保留，只有普通攻击回退。其他动作、模型、伤害、时序和配置没有被旧蓝图文件覆盖。

回退记录：[rollback_melee_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV17/rollback_melee_receipt.json)。Beast06／ArmChainV15 的普攻方案保留为历史制作资料，后续不作为本次小改的动作源。

## 从旧版制作的 ClawV17 候选

直接读取 `ClawV16/Delivery/MantisM27_ClawV16.blend` 中两段密集原始动作；保留原挥镰方式、刃面、身体发力、脚部支撑与首尾姿势，仅调整整身共用的局部时间映射：

| 范围 | 处理 |
|---|---|
| 0.00–0.16 秒 | 起步稍缓，再平滑接回旧进度；原 0.045 秒的姿态对应新 0.060 秒 |
| 0.16–0.36 秒 | 直接使用原时刻的原姿态，保留蓄力峰值、挥击、接触、制动和回震 |
| 0.36–0.65 秒 | 收势前段略快，末段减速收住；原 0.50 秒的姿态对应新 0.48 秒 |

没有混入 Beast06 或 ArmChainV15，没有重新计算肩肘、刀弧或避让。两段时长仍为 **0.65 秒、60 fps、40 个采样点**；接触窗仍为 **0.25–0.30 秒**，额外恢复仍为 **0.10 秒**。制作参数不代表观感已经通过用户检查。

独立候选：`/Game/Monsters/MantisM27/ClawV17/BP_MantisM27_ClawReviewV17`。候选复制回退后的正式角色，只替换普通攻击，飞扑沿用 V11。正式 F6 保持原版 ClawV16，未由候选导入替换。

## 交付记录

可编辑源和两个 FBX 已导出，两段 UE 动画与独立候选蓝图均已后台导入／保存，commandlet 退出码为 0，记录见 [ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV17/ue_receipt.json)。本轮仅后台制作、导入和保存，未运行测试、渲染、PIE 或游戏。

- [作者源与导出](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV17/Delivery)
- [制作参数](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV17/Delivery/motion_manifest.json)
- [作者脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/ClawV17/author.py)
- [回退脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/ClawV17/rollback_melee.py)

动作沿用 ClawV16 的本地 Epic Paragon Khaimera 派生来源，保留原 UE 许可，不是 CC0。
