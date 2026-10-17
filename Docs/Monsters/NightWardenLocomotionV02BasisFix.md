# 守寝者移动动画坐标修正 V02

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

**后续用户反馈：整体仍然过度扭曲，本版没有通过用户认可。用户已要求撤下全部衣物并恢复最初的 Meshy 模型；当前恢复记录见 [V06 原始模型恢复](NightWardenOriginalRestoreV06.md)。** 下述坐标数据仅是历史局部诊断，不作为整体角色、动作或衣物合格的依据。

用户反馈 V01 播放后整体倒伏、衣物及肢体扭曲。源 Blender 和新导入 FBX 的五个对应姿态保持一致；UE V01 的骨盆在首帧由应有的约 138.8 cm 高度变成 X=-138.8 cm、Z=-0.99 cm，头部最大位置误差约 353 cm。

原因是 V05 模型与 V01 动画都采用 `force_front_x_axis=True`，但 V01 额外设置了 `preserve_local_transform=True`。本地 UE 5.8 `SkeletalMeshEdit.cpp` 的动画导入分支表明，这会直接采用 FBX 局部矩阵，绕过模型绑定所用的 `GetJointPostConversionMatrix()`。动画和参考骨架的坐标不一致，导致播放变形；根骨本身的 100 倍单位缩放保持一致，不是将角色或关节继续乘 100 能修复的问题。

修订统一动画导入坐标转换，设 `preserve_local_transform=False`，重新生成独立的 `A_NightWarden_Walk_V02`。沿用原 2.8 秒步态、V05 模型、衣物、材质、蒙皮和手电。

随后发现 `NW_Flashlight` 在 1.4 秒的导入局部旋转偏离源文件约 20.2°。源文件中该骨始终保持固定的 `Bone_019` 掌部相对变换，修订按同一参考变换烘焙恒定四元数轨道，消除该次挂点突转，不改变持灯手臂动作。

## 当前状态

已通过后台 commandlet 实际保存动画 `/Game/Monsters/NightWarden/Animations/LocomotionV02/A_NightWarden_Walk_V02`，并将原 `/Game/Monsters/NightWarden/BP_NightWarden` 切换到 V02 原地循环。保存回执为 `LocomotionV02/Records/ue_delivery.json`，`animation_and_entry_saved`、`complete=true`；最终 commandlet 退出码 0，原有插件 Python 同名警告不属于本动画错误。

针对此次扭曲，对比 0、0.7、1.4、2.1、2.8 秒五个姿态：UE 原始轨道与 Blender 的最大关节位置差为 0.000354 cm，蒙皮旋转差 0.000590°；UE 压缩轨道的最大位置差为 0.327 cm、旋转差 0.140°。原来约 353 cm 的坐标偏移已消除。这是局部数据排查结果，不代表游戏视觉验收。

F6 的“守寝者（模型与衣物）”重新生成后使用 V02。身体、衣物、材质和模型骨架资产未修改；仍为原地动作预览入口，未增加 AI 位移或战斗。

## 制作及诊断输入

- 有效动作源与 FBX：`SourceAssets/NightWarden20261015/LocomotionV01/Authoring/NightWarden_Walk_V01.blend`、`LocomotionV01/Exports/A_NightWarden_Walk_V01.fbx`。
- 导入：`Scripts/import_walk_v02.py`；使用同一 FBX，重新应用模型一致的关节坐标转换。
- 接入：`Scripts/activate_walk_v02.py`；后台入口 `Scripts/motion_background_v02.ps1 -Stage Import` 在同一互斥批次完成导入、定点数据对比和入口保存。
- 针对此次错误的诊断：`Scripts/diagnose_walk_blender_v02.py`、`diagnose_walk_ue_v02.py`、`compare_walk_basis_v02.py`。
- 数据：`LocomotionV02/Records/source_pose_diagnosis.json`、`fbx_pose_diagnosis.json`、`ue_pose_diagnosis.json`、`ue_corrected_pose.json`、`basis_comparison.json`。中间的手电异常保留在 `ue_before_torch_anchor_fix.json`。

仅针对用户反馈做源/FBX/UE 原始及压缩姿态对比；没有主动启动游戏、PIE、渲染或全面回归。自然度、衣物穿插和最终游戏观感仍由用户体验。
