# 螳螂 M27 左右普攻 V2 接入

**2026-11-09 最新状态：已回退普通攻击。** 用户要求恢复修改前版本，正式与当前对比角色的普攻已恢复本次接入回执所记录的 ClawV16。本文以下 V2 接入说明为历史记录。后续直接从旧版制作的微调候选见 [ClawV17](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27ClawRollbackAndV17_20261109.md)，正式飞扑仍为 PounceV11。

2026-11-08。用户要求继续，并自行检查。本轮完成右攻击精修，将已制作的左攻击与新右攻击一起接入正式 F6 螳螂及已有对比蓝图。未运行渲染、离线验收、PIE、游戏或联机测试。

后续更新：[八阶段飞扑 PounceV12](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV12EightPhases20261108.md) 曾接入正式蓝图，用户检查后认为不如旧版，已恢复 PounceV11 并保存。左右普攻仍为本版 V2。新的 [PounceV13](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV13LocalTiming20261108.md) 单独作为局部节奏候选，不替换正式飞扑。

## 当前可使用版本

正式入口仍为 `/Game/Monsters/MantisM27/BP_MantisM27`，稳定 ID `MantisM27`。在工程游戏中用 F6 重新生成螳螂，现有普攻交替逻辑会选择左、右 V2；已生成实例不作为本次新默认引用的检查对象。

| 动作 | UE 资产 | 制作区别 |
|---|---|---|
| 左攻击 | `/Game/Monsters/MantisM27/Beast06V2/Animations/A_M27_LeftSlash_Beast06V2` | Attack1 身体参考，斜切、换重、随势切出与弧线回收 |
| 右攻击 | `/Game/Monsters/MantisM27/Beast06V2/Animations/A_M27_RightSlash_Beast06V2` | 独立读取 Attack6 原生重定向数据，较短的横向回钩、左后脚抬跟转掌、回震后收势 |

右攻击没有镜像左动作的骨骼轨迹。它使用 Attack6 自身的躯干与臂链源数据、独立的非线性时间映射，并将整条右臂适配到近水平的切削平面；左副刃向外后侧收回。刀刃方向由实际刃面与带符号的曲刃坐标决定，肩部修正携带完整臂链，不单独扭腕或弯曲刚性刀刃。

两段均为 **0.65 秒、60 fps、40 个采样键**。保留原 **0.25–0.30 秒命中窗口**和 **0.10 秒额外恢复时间**。

## 实际保存范围

正式蓝图与 `/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1` 均已编译并保存，修改的动作字段只有：

- `attack_clip` → 左 V2。
- `left_slash_clip` → 左 V2。
- `right_slash_clip` → 右 V2。

正式蓝图之前的三个字段来自 ClawV16；旧动画资产继续保留，原引用记录在 [activation_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/activation_receipt.json)。正式待机仍是 BindingV2，移动仍是 RunV4，飞扑仍是 PounceV11。其他候选动作、伤害、隐身、AI、音效与数值没有随本轮替换。

没有 C++ 变化，不需要原生模块构建。本轮完成的是 FBX 导出、动画导入、蓝图引用接入及保存；commandlet 退出码为 0。保存成功不代表用户已认可动作，也不代表实战接触或穿模验收通过。

## 制作源与记录

| 内容 | 路径 |
|---|---|
| 左制作源 | [MantisM27_Beast06V2.blend](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/Delivery/MantisM27_Beast06V2.blend) |
| 右制作源 | [MantisM27_Beast06V2_Right.blend](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/Delivery/MantisM27_Beast06V2_Right.blend) |
| 左参数 | [motion_manifest.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/Delivery/motion_manifest.json) |
| 右参数 | [motion_manifest_right.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/Delivery/motion_manifest_right.json) |
| 右制作脚本 | [author_right.py](D:/FPS3D/FPSGAME/Tools/MantisM27/Beast06V2/author_right.py) |
| 正式接入脚本 | [import_activate_pair.py](D:/FPS3D/FPSGAME/Tools/MantisM27/Beast06V2/import_activate_pair.py) |
| 实际保存记录 | [activation_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/activation_receipt.json) |

本轮不更新旧 GIF；Beast06V1 的预览不能代表现在的左右 V2。左攻击前一阶段的制作说明见 [左攻击 V2](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27Beast06V2LeftAttack20261108.md)，飞扑尚未执行的细分方案见 [升级计划](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27Beast06Upgrade20261108.md)。
