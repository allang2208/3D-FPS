# 巫婆动作基础候选

**2026-09-21 状态：用户试玩认为此人体粗模没有问题，作为后续外观重建基础保留。** 当前只有待机与移动，不代表最终巫婆外观、攻击与完整战斗已经认可。整项巫婆开发按用户要求暂停，见 `Docs/Backlog.md` W1–W3。本目录及其 UE/F6 入口不属于废案。

用户已同意先重建站立与持杖慢走基础，再判断是否开展最终巫婆外观。此目录保存独立候选，不覆盖此前巫婆。

## 来源与保留

- 人体：本机 UE 5.8 模板的完整 `SKM_Quinn_Simple`；保留原始拓扑、腿脚、蒙皮和手指，不再拼接供体肢体。
- 动作：同一 Epic Mannequin 骨架的 `MM_Idle` 和 `MF_Unarmed_Walk_Fwd`。原始 FBX 位于 `Sources`；动作时长和导出路径见 `source_motion.json`。
- `template_sources.json` 记录本机模板路径及复制文件散列。Epic 资源遵守其适用许可，不视为公共领域资源，不将原始模板素材公开再分发。
- 原巫婆部件继续保存在 `SourceAssets/WitchMeshy20260919/Authoring/LayeredV04/Preserved`：未切母版、头发与头、帽、上衣、原裙参考、双手、法杖、毒瓶及 PBR。此次未改变这些资产。
- 运行时道具复用 `/Game/Monsters/WitchMeshy/Props/SM_Witch_Staff` 和 `SM_Witch_PoisonBottle`。

## 候选结构

`Authoring/WitchFoundation_Idle.blend`、`WitchFoundation_Walk.blend` 是完整人体可编辑源；`Delivery` 为动作 FBX，`Authoring/motion_manifest.json` 包含帧数、原始支撑脚速度曲线和抓握参考。

UE 独立目录为 `/Game/Monsters/WitchFoundation`，保留完整 Quinn，暂用哑光深色材质呈现动作基础。头帽、最终裙装及对应的材质细节待用户判断基础动作后适配；当前简化人体不是最终巫婆美术。

原生动画驱动使用待机／行走混合、FK 到 IK 目标拷贝、步幅调整、FootPlacement 和 LegIK。源行走为 300 cm/s，候选步幅比例为 0.5、最大移动速度 82.5 cm/s，对应满速播放倍率 0.55；播放速度由实际速度驱动。支撑曲线来自去除根位移之前的源脚掌速度。全身源动作保留重心与左右相位，躯干前倾分布在脊柱上，双臂与手指另作持物姿态。

F6 → 怪物生成 → **巫婆·动作基础候选**。远离玩家时接近，约 2 m 附近停止；这一阶段只有待机与移动，支持面板清除。原“巫婆”仍保留原有战斗逻辑。

未启动 PIE、渲染或进行运行测试；由用户实际判断。编译／导入完成只代表接入，不代表步态、手指接触或地形贴合已通过视觉验收。`ue_delivery.json` 记录资产保存及原生绑定阶段。
