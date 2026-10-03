# M-07 LocomotionV10：大跨步与人体摆臂

用户要求移动时步子稍大，手臂按照人体大跨步前后摆动，并重做移动中的手腕和手部表现。制作只替换 SlowWalk、Chase，沿用 OriginalV09 原网格、UV、权重、布料及 V08 的 83 骨参考。其他动作、攻击接触时间和导航继续保留。

## 动作来源

本地原始 Epic 空手走路：`SourceAssets/WitchFoundation20260920/Sources/Walk.fbx`，源资产 `/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd`；45 个帧间隔、30 Hz、1.5 秒。完整身体与双脚、双臂使用同一个源相位，保留肩胸与骨盆的配合。来源记录为同目录的 `source_motion.json`、`template_sources.json`；本机 UE 模板适配，仅用于本工程，不作为可独立再分发的动作库。

库内还包含 CC0 Mesh2Motion `Walk_Large`、`Walk_Female`、`Walk`、`Jog` 等整身动作。本次选用已有干净 Epic Walk，以延续已使用的同相位双足参考。

## 制作参数

| 动作 | 完整左右脚周期 | 源移动速度 | 每步制作长度 | 相对 V08 | 手臂前后摆动 |
| --- | --- | --- | --- | --- | --- |
| SlowWalk | 2.0 s | 90 cm/s | 90 cm | +20% | 后摆 20°、前摆 24° |
| Chase | 44/30 s | 145 cm/s | 约 106.3 cm | 约 +22.2% | 后摆 28°、前摆 32° |

移动速度保持原值，通过更长的完整步态周期匹配扩大后的脚部行程。脚掌轨迹、支撑相和足部滚动来自同一原动作；使用原双足骨长与原解剖弯曲平面求解，伸展末段按可达高度微调骨盆，保留落脚目标。手臂使用源动作的对侧时序，肘部按源屈伸节奏变化，手腕跟随前臂并加入小幅滞后，手指保持原人体骨链上的轻曲姿态。帧零保留真实参考姿态，排除在两个导出片段之外。

## 交付状态

两段 FBX 与完整可编辑组合源已保存于 `SourceAssets/BlindSupplicantM07Meshy20261001/LocomotionV10/`。SlowWalk、Chase 已实际后台导入 `/Game/Monsters/BlindSupplicantM07/AnimationsLocomotionV10`，复用 `SK_M07_ReferenceOriginalV08` 和 `SK_M07_OriginalV09`；实际片段时长为 2.0 s 和约 1.4667 s。

现有 AI/F6 蓝图的 `slow_walk_clip`、`chase_clip` 与 `walk_clip` 引用已保存，原生默认的两段步态引用同步更新；移动和源动作校准速度仍为 90/145 cm/s。十个非移动动作及攻击接触时间保留。实际保存回执为 `LocomotionV10/ue_locomotion_delivery_v10.json`。

Editor/Game 后台构建成功，记录为 `Saved/BuildEditor/m07-FPSGAMEEditor-20261002-145542.log` 与 `Saved/BuildEditor/m07-FPSGAME-20261002-145557.log`；实际导入记录为 `Saved/Logs/M07Import-20261002-145527.log`。

没有启动游戏、播放、渲染或自测，实际外观与移动由用户通过 F6 重新生成测试。
