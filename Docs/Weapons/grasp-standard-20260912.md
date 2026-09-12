# 抓握经验标准化与废案归档，2026-09-12

用户先认可垂直握把的 VRE 抓握方向，随后明确确认同法完成的 45° 侧倾握把、棱镜阻手器“成功了”，授权更新配件标准、技能、trash 与 Git。此轮为文档与归档，没有改动画、游戏数值、运行选择或材质。

## 当前方法

[改造配件标准](../../skills/ue5-weapon-workflow/references/attachment-standard.md) 已将握把接触分支改为：先实际查看并复用成组手型，四指弯曲包握、拇指横扣；先调统一闭合幅度、整手方向和握点，再沿原肩肘来向处理腕臂。腕轴接近直线也可能严重扭转前臂，必须同时看 twist、肘平面和实际玩家视角。小阻手器按用户许可整体包在自然拳形中，内部穿模可接受。

[抓握类别与当前路径](../../skills/ue5-fps-arms-animation/references/vertical-grip-family.md) 统一了此前多个“当前母版”描述。垂直/斜握把 80%、小阻手器 90% 闭合与斜握把 75% 原腕方向混合仅是本骨架参数；跨枪复用指型，每枪重新校准挂点和手臂。主要换弹接触、右手、枪械机械轨道及业务时钟保持；验证四元数时处理 q/-q 等价。

两个 SKILL.md 入口及五份相关参考已同步到个人技能目录与工程镜像。来源及许可仍按 [VRE 来源记录](../../SourceAssets/MannyGraspDonor20260912/README.md)，不上传原始模型、动作矩阵或衍生二进制。配件数值迁移按既有枪匠数据核对，不因姿态成功扩大属性修改范围。

## 已确认结果与证据

- [垂直握把](../../SourceAssets/MannyGraspDonor20260912/README.md)：M4/AKM 各九动作，源合同与 UE 回读 18/18，历史两组游戏回归通过。用户先确认改善方向。
- [45° 与阻手器](../../SourceAssets/VREGripExtensions20260912/README.md)：M4/AKM 四族各九动作，源合同与 UE 回读 36/36，历史四组游戏回归通过。用户现已确认成功。
- 两例的 validation.json 仅更新用户确认状态及历史材质表述，制作时的运行、测量和非零 commandlet 退出边界保留；没有把本次文档检查写成重跑 UE 或零穿模证明。

## 归档边界

精确移动清单见 [grasp-archive-20260912.json](grasp-archive-20260912.json)，脚本为 [archive_grasp_candidates_20260912.ps1](../../Tools/AssetPipeline/archive_grasp_candidates_20260912.ps1)。归档根为本机 `D:/FPS3D/FPSGAME/trash/grasp-workflow-20260912/`，按原工程相对目录保存，移动前后均校验 SHA-256，不删除素材。

范围包括：明确拒绝的前伸拇指输出/搜索脚本与候选渲染、完全闭合早期动画及同名旧报告、退握修复前备份、严格按斜握把轴对齐导致扭臂的姿态试验，以及这三个制作目录中有对应正式 Blend 的自动备份。

保留：两例 Final 的 114 个正式 Blend/FBX；VRE 原始姿态、来源/许可、统一闭合对照；当前姿态参数与诊断方法；VerticalGripFront、VerticalGripErgonomic、CantedGripMigration 中实际被生成器、源合同和 UE 回读引用的旧动作；全部有效冻结参考和游戏证据。旧方案里的两份拟合种子先以同散列迁入 ReferenceWorkflow，见 [保留参数记录](grasp-retained-seeds-20260912.json)，原废案包随后归档。旧文档快照在同一 trash 的 BeforeDocs，现有 Docs/VerticalGripClass.md 改为单一标准入口。

废案 Blend 是原字节归档，内部相对依赖可能仍以原作者目录为基准；历史取证若需要打开，按清单恢复到隔离的原目录结构，不覆盖当前正式动作。Content 中仍被源对照、读回和现有配件引用的资产不列为废案。

本次按宿主 [WORKFLOW](../../WORKFLOW.md) 第 8 节，仅提交工作流、验收状态、归档清单和相关作者入口变更；trash、姿态种子和二进制不公开。校验结果见 [整理验证](grasp-standard-validation-20260912.json)。
