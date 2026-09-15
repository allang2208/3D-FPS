# 双持手枪作者源

适用 M1911 和 DW715，当前运行引用来自 `Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp`。

| 当前分支 | 制作参数 | Blender 参数 | UE 导入参数 |
| --- | --- | --- | --- |
| 基础握姿/射击/装备；M1911 换弹 | `NaturalAimV3/pose_profile.json` | `-- M1911` 或 `-- DW715` | `-DualNaturalAimUpdate` |
| 连续奔跑 | `SprintSmoothV5/sprint_profile.json` | `-- M1911 --sprint-smooth` 或 `-- DW715 --sprint-smooth` | `-DualSprintSmoothUpdate` |
| 双持左轮甩仓 | `RevolverReloadFlickV6/reload_profile.json` | `-- DW715 --revolver-reload-flick` | `-DualRevolverReloadFlickUpdate` |

Blender 入口为 `author_dual.py`，UE Python commandlet 入口为 `import_dual.py`。默认 UE 导入恢复两只手的初始网格，之后分别导入三类当前动画。已有网格时可直接执行当前动画的导入参数。

V2 握姿、V4 奔跑、最初的动画输出以及 V3 中已经被 V5/V6 替代的单独 FBX/uasset 已归档。作者和导入器不会在正常入口恢复这些废案；V3 的可编辑 Blend 仍保留当前基础动作和历史动作集合，不因部分片段退役而丢失有效作者源。

完整本机恢复仍需本目录初始 `M1911/{r,l}`、`DW715/{r,l}` 网格 FBX 和原始 `*-authoring.json`，以及三个当前版本的 Blend/FBX、作者清单和导入记录。该元数据保留本机，不是可公开再分发的完整模型包。旧初始动画路径可能保留在历史清单中，默认导入器只读其中网格。

上游输入：`M1911Contact20260913/M1911_Contact_Editable.blend`、`M1911ReloadTiming20260913/M1911_ReloadReady_Editable.blend`、`DanWesson715Upgrade20260914/DanWesson715_Upgrade_Editable.blend`、`DanWesson715LeftRecovery20260914/DanWesson715_LeftRecovery_Editable.blend`，及其 Manny/材料/骨架依赖。源网格、骨架和第三方素材沿用原许可；本次 Git 仅发布作者代码与原创动作参数。

`SprintSmoothV5/inspect_sprint.py` 和 `compare_samples.py` 是此前用户授权诊断时的工具，本次未运行；默认采样版本更新为当前 V5。若主动选 V4，需要先恢复相应历史资源。原诊断数据仍留本机，不将历史结果表述为本次重新验收。

整理记录：`Docs/Weapons/pistol-publication-20260915/README.md`。本轮无游戏测试或视觉验收。
