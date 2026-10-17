# 守寝者移动循环 Locomotion V01

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

**2026-10-16 用户反馈：UE 播放后整身倒伏、衣物及肢体扭曲，本版引擎导入结果被否定。** 作者源与 FBX 的姿态一致；定位到动画导入的 `preserve_local_transform=True` 绕过了模型使用的 joint post-conversion。修复进展见 [V02 坐标修正](NightWardenLocomotionV02BasisFix.md)。下文保留 V01 制作与历史保存信息，不能视为用户认可或当前可用交付。

已制作并保存一条 2.8 秒、60 FPS、169 个采样的原地行走循环。正式动画资产与原 `BP_NightWarden` 入口均已保存；后台导入退出码为 0。F6 的“守寝者（模型与衣物）”重新生成后循环播放该动作。

## 动作制作

- 以现有 `ZombieAnimationPack/anim_Walk_B` 的完整步态为来源，使用 `SourceAssets/FacelessSecurity20261008/V05/Native/native_walk.json` 中已保留的原生重定向动作输入。
- 按两者实际肩部横向和竖直方向对齐动作坐标；将源脚步轨迹按腿长适配，并限制前后步幅。最终腿部由目标自身的髋—膝—踝长度解算，保留守寝者骨长，不直接复制供体关节位移。
- 保留源动作的错峰落脚和摆动节奏，重心降低约 9.5 cm，加入受承重影响的小幅侧移；肩背和头部保留原驼背形态并叠加受限的周期运动。
- 右侧巨臂约滞后 0.21 秒跟随身体，手指为较松的爪形；左臂使用双段解算稳定持灯位置，四指与拇指制作握持姿态。手电仍跟随原掌部挂点。
- 承重位置来自实际靴底支撑点，承重阶段趋于平放，摆腿抬高上限约 8.5 cm。该处理是平地动画制作，不包含运行时地形 IK。
- 循环末帧与首帧一致；根骨保持原地，局部骨骼使用单位缩放。保持 V05 的身体、衣物、材质、骨架和蒙皮，不重制几何。

制作得到的支撑脚后移参考速度约 74.6 cm/s，仅作为以后实际移动与动画播放倍率匹配的参考。当前 F6 Character 仍为动画预览入口，没有增加 AI、寻路、追击或战斗。

## 输入选择和制作边界

首次直接向守寝者做 UE IK 重定向，得到的腿部主要运动方向为横向，组件位移也明显缩小，未用作最终成品。该批次完成源数据落盘后，在退出时发生动画压缩任务重复 Hash 的引擎断言；原记录保留在 `LocomotionV01/Records/Retarget-stdout.log`。

最终改用已有 Walk_B 供体数据，经过解剖方向配准、周期姿态适配及目标定长肢体解算后，独立导出并正常导入。没有用失败的直接重定向结果作为最终动画，也没有把其退出异常写成构建成功。

## 交付

- 作者源：`SourceAssets/NightWarden20261015/LocomotionV01/Authoring/NightWarden_Walk_V01.blend`。
- FBX：`LocomotionV01/Exports/A_NightWarden_Walk_V01.fbx`，包含与 V05 相同的参考骨架和蒙皮，UE 仅导入动画。
- 正式动画：`/Game/Monsters/NightWarden/Animations/LocomotionV01/A_NightWarden_Walk_V01`。
- 入口：`/Game/Monsters/NightWarden/BP_NightWarden`。单节点模式、原地循环、播放倍率 1；使用可序列化的 `OverrideAnimationData` 保存默认播放设置。
- 制作：`Scripts/author_walk_v01.py`；导入：`Scripts/import_walk_v01.py`、`Scripts/motion_background_v01.ps1 -Stage Import`。
- 制作合同：`LocomotionV01/Records/motion_manifest.json`；保存回执：`LocomotionV01/Records/ue_delivery.json`，状态 `animation_and_entry_saved`、`complete=true`。

没有启动图形编辑器、游戏、PIE、渲染或动作验收测试。动作观感、衣物动态穿插和手电握持效果由用户查看；本轮不宣称经过视觉验收。
