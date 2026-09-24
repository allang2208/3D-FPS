# 裸皮感染犬：Godot 奔跑自然度细化 V3

用户反馈 GodotRunFitV2 已有改善，要求进一步自然化。本版本沿用同一 Godot Gallop 与裸皮犬绑定，已制作、导出、导入并保存；未启动游戏、预览或验收渲染，实际观感由用户确认。

后续用户确认“基本成功，可以作为四足犬科的模板了”。本版本作为已认可的犬科奔跑基线保留；适用于此 41 骨绑定及体型，其他犬类仍需按自身骨架、肢长和步幅适配。后续攻击与 AI 优化见 [狩猎升级记录](../../../Docs/Monsters/InfectedDogHunting20260925.md)。

## 来源与范围

原动作来自 Quaternius Ultimate Animated Animals 的 Gallop，CC0-1.0，来源页 <https://quaternius.com/packs/ultimateanimatedanimals.html>。使用 Godot 归档提交 `49cec1dd11d65295f43c737bac327de829cfd7b1`；原始输入保留在 `../GodotRunFitV2/Source/`，本轮直接读取其中 `godot_gallop_samples.json`。

保留 17/30 秒循环、原四足相位和腾空节奏、现有 41 骨绑定与 7.5 cm 跑姿屈腿余量。没有修改模型、权重、骨架参考姿态、材质、物理资产或其他动作。

## 动作细化

- 在腿链求解前平滑循环源控制点，并以周期插值烘焙到 120 Hz、69 个含闭环端点的关键帧，减少回收和循环衔接的突变。
- 支撑期足端向统一的后向行程拟合，逐渐稳定横向位置和足底高度；抬腿阶段保留源轨迹。脚趾与腕部仅在支撑期逐渐靠近目标脚掌的中性方向。
- 跗关节接近腿长限制时增加 3.5 cm 范围的渐进过渡，保留前肢肘向后、后肢膝向前的弯曲方向。
- 身体垂直起伏保留 90%，颈部与头部角度变化分别保留 88% 和 68%；肩胛增加 35% 随目标胸部转动的配合，耳朵跟随头部。
- 尾巴沿原动作增加从根部 12 ms 到尾尖 47 ms 的逐段延迟。

动画步幅参考速度为 `286.754931767184 cm/s`，仅供现有移动驱动的动画相位使用。角色实际追击速度仍为 400 cm/s；没有将跑步固定为 1 倍速，也没有增加运行时 IK。

## 已保存入口

`/Game/Monsters/InfectedDog/MeshyV2/GodotRunNaturalV3/A_InfectedDogMeshy_GodotRunNaturalV3`

正式 `DA_InfectedDogMeshy_AnimationSet` 的 Run、RunTurnLeft、RunTurnRight 已引用此动作，左右转向仍由角色驱动。其他动作的引用、播放参数、命中窗口，以及六维、感染、AI 和 F6 身份保持原设置。

导入沿用目标 Skeleton，并恢复动画单独导入时丢失的根单位转换，使动画根缩放匹配约 100 的绑定根。只保存新动画和上述 AnimationSet，没有重新导入身体网格。

## 制作、保存与恢复

- 母版：`InfectedDog_GodotRunNaturalV3.blend`。
- 引擎导入源：`A_InfectedDogMeshy_GodotRunNaturalV3.fbx`。
- 参数与制作记录：`authoring.json`、`foot_goals.json`。
- 实际保存回执：`installation.json`，状态 `assets_saved_and_run_bound`。
- 替换前引用和数据资产：`binding_before.json`、`DA_InfectedDogMeshy_AnimationSet.before.uasset`。GodotRunFitV2 动画资产保留。
- 生产入口：`Tools/InfectedDog/author_godot_run_natural.py`、`Tools/InfectedDog/install_godot_run_natural.py`。若重做 CompletionV2 全量安装，应最后执行本安装入口。

本轮通过已有编辑器的互斥桥完成导入与保存，没有打开新编辑器或执行保存后测试、动作采样、截图、渲染及 PIE。制作求解记录和成功保存不代表游戏内接地、穿模或观感已获验收。
