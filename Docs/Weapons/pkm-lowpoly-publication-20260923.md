# PKM 低模重建：当前恢复与源码发布

2026-09-23。本记录对应用户提供的 Sketchfab `pkm_machine_gun.glb` 和 `SourceAssets/PKMLowpoly20260922`。早期 Meshy `PKM20260921` 已退役，见 [历史废案](pkm-retirement-20260922.md)；该退役不包括这里的低模重建分支。

## 当前内容与入口

- 主网格：`/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular`；私有骨架：`/Game/Weapons/PKMLowpoly20260922/SK_PKM_Manny_Skeleton`。当前网格从 HandleFinish27 的提把修订导出，再由 Hands29 修复导出 UV 通道；源 Blend 与有效旧输入继续保留。
- 材质：Finish20 的枪体／配件干湿映射，HandleFinish27 哑光微纹，AmmoBox30 的新旧弹箱独立绿色漆面；瞄具连接座为 OpticMount23。共用 Manny 手部外观与木材、聚合物、光学区域分别保留。
- 动作：基础 `Animations/A_PKM_*` 和 `Accessories14/Animations/<family>/A_PKM_<family>_*`，包含基础、vertical、canted、prism、angled。EquipCharge31 保留装备动作，Charge34 仅更新五类空仓换弹尾段；Reload16 普通换弹、Feed13 供弹、Combat17 冲刺及 Melee24 近战仍在各自分支。
- 动态：`PKMCarryHandleDynamics`、`PKMOutgoingBeltDynamics`、`PKMSoftBeltDynamics`、`PKMExitCoverDynamics`。弹链按生成序号逐节退场，受约束的柔性链先求解，盖板随后避让；这些是游戏表现动态，不是整枪刚体仿真。
- 脚架：Bipod26 三分件模型与 `PKMBipodComponent`，独立 `bipod` 改造槽默认空。`WeaponBipodDeploymentComponent` 在进入 ADS 时尝试部署、取消 ADS 时退出；范围、开销、属性及 UI 详见 [脚架部署](pkm-bipod-deployment-20260923.md)。
- 声音：普通机械接触来自 `ReloadAudio22`，空仓后拉／后止／前推／前止改用 `ChargeAudio35` 的四段原视频混音裁切；源时点分别为 5.13／5.36／5.48／5.82 s。专用开火声沿用已发布的 `SourceAssets/PKMLowpolyAudio20260922`。

## 作者源与恢复依赖

公开目录保存作者脚本、HLSL、说明、少量设置与音频来源元数据。完整编辑还需要合法本机资产：原始分件 GLB、Manny 手臂与现有武器动作、QBZ-191／AKM／配件源材质和模型、密集骨骼／几何读取结果、各阶段 Blend/FBX、贴图、视频和音频。不是从 Git 单独克隆即可还原的完整资源包。

| 内容 | 当前入口／保留依赖 |
| --- | --- |
| 主体、提把、出口盖板 | HandleFinish27 → Motion21 → OutgoingBelt19 → CarryHandle18 → Accessories14；Hands29 使用共用 Belt08 导出器修正 UV0 |
| 表面、绿色弹箱与雨天 | Finish20 → HandleFinish27 哑光；AmmoBox30 在已有干湿材质上建立弹箱覆盖；Belt08/material_binding.py 保持语义映射 |
| 空仓后拉前推 | Charge34/author_charge.py → EquipCharge31/author_actions.py 和五类 Blend → Reload16 作者函数；保留正确的旧插值函数以撤销旧烘焙运动 |
| 原声音效 | ChargeAudio35/author_audio.py → 本机 References/PKM_UserReloadReference.mp4；导入复用 BeltAudio22/import_audio.py |
| 脚架与握把 | Bipod26、BipodDeploy28 的脚底坐标；GripContact15、GripMount25 与各握姿家族、现有通用配件源 |

这些脚本带有本机制作路径，按目标阶段运行，不能将所有历史导入器按目录名顺序盲目重跑。低编号脚本可能覆盖高编号网格或材质。最新导入保持原骨架参考姿态，并恢复材质／分段身份。恢复现用包时，成套保留 `/Game/Weapons/PKMLowpoly20260922` 及上述外部依赖，遵守 [AssetSetup](../AssetSetup.md)。

## 来源与发布边界

模型作者和原许可记录见 [SOURCE](../../SourceAssets/PKMLowpoly20260922/SOURCE.md)：EXcaliburK117 / EXcalibur117，用户提供的 Sketchfab Standard 来源，记录有 NoAI 标记。此次为本机确定性建模与材质处理，未向生成服务上传该模型。

视频由用户指定为 [BV1jHeA6sEmj](https://www.bilibili.com/video/BV1jHeA6sEmj/)。声音是成品混音裁切，不是独立原游戏音效分轨。模型、Manny、复用材质／配件、原视频及衍生音频分别沿用其来源边界；本轮不把它们公开上传，也不把制作脚本的公开视为原资源授权。原始与衍生二进制、密集采样和导入回执仍保留本机。

## 本次归档

共 31 个文件、139,518,283 字节移入本机 `trash/pkm-lowpoly-publication-20260923/`：26 份已有正式 `.blend` 对应的 `.blend1` 自动备份，以及 ChargeAudio35 的 5 份可重建解码／变速中间 WAV。最终四段 WAV、原视频、作者 Blend、当前 FBX、正式 UE 包、导入前恢复备份及关键历史证据均保留。

逐项原路径、目标、大小、SHA-256、理由及替代物见 [归档清单](pkm-lowpoly-archive-20260923.json)。移动前限定绝对路径属于本任务根，移动后散列读回一致。`trash` 本体不提交 Git。

## 交付状态

前一轮五个空仓动画与四个 SoundWave 已导入保存；常规 FPSGAMEEditor 构建最终成功，记录为本机 `ChargeAudio35/build_editor_delivered.log`。本次只做归档、SKILL 沉淀与发布检查，没有启动 UE、重新构建、运行游戏或试听验收。共享源码按 PKM 范围逐块发布，保留 SVD/PSO-1、移动、近战、冶炼等并行工作。公共子集未单独构建，不将宿主构建结果冒充公共仓库独立恢复验收。

发布范围检查还发现既有 HEAD 的 `FPSGAMECharacter.h` 已引用未入库的 `WeaponReloadStages.h`，相关换弹检查点实现仍属于并行制作文件；本次不夹带发布整个并行模块，也不宣称公共仓库可独立构建。原有角色代码已引用 SVD 冲刺枚举，因此本次枚举声明保留该兼容值，但不发布并行 SVD 动作实现。个人与工程技能的本次 PKM 段落一致；两个手臂文档中既有的其它主题差异保留，不为同步本次经验覆盖它们。

经验入口：[PKM 分件、材质与部署](../../skills/ue5-weapon-workflow/references/pkm-lowpoly-mechanics.md)、[动作接触与收势](../../skills/ue5-fps-arms-animation/references/reload-handoff.md)、[视频原声音效](../../skills/ue5-weapon-workflow/references/weapon-audio.md)。
