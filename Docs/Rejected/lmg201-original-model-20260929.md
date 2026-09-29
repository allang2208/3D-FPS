# 原 201 模型废案记录

2026-09-29 用户明确要求将原 201 模型记为废案，并整理本条开发线的其它废案。范围是首轮照片／三视图生成的 201，不是当前重新生成的新模型，也不涉及其他武器或并行任务。

## 否定范围

- 首轮 Meshy 任务 `01a0e307-6875-71b9-a025-882278f5a49b`，原始 `Meshy`、`ModelV01`、`InputsV01`、`ReferenceV01` 与 Authoring 主体。
- 原模型历次机匣、机瞄和手部局部重求解并未得到整体认可。盖体、弹链、抓握及肩肘腕反复失配，不能因导入成功、增加面数或版本号更高称为成功母版。
- 原金属弹箱换弹方案以及 PKMDirect09、Reload11、Joint16、WholeArm17 等旧调整不再作为现用布袋换弹模板。ArmNatural18 此前已在 `trash/lmg201-armnatural18-rejected-20260928`，保持原位置。
- Video26 向枪管和主体扩展的表面升级曾被用户要求回退；新模型 Detail35 的失控盖内壁输出也已退役。Repair36 从加厚前外皮重建，不能恢复 D35 的尖刺输出。

## 已归档与保留

本次 **962 个文件，22,020,397,535 字节**（含 116 个 UE 包）移至本机 `trash/lmg201-rejected-20260929/`，没有删除文件。每项原路径、目标、大小、SHA-256、原因和替代物见 [归档清单](../Weapons/lmg201-publication-20260929/archive-manifest.json)，移动后散列一致。

50 个候选旧 UE 包仍有外部引用，保留清单及引用来源见 [引用记录](../Weapons/lmg201-publication-20260929/archive-references.json)。其中包括枪匠展示模型所用的旧材质；不能为目录整齐破坏其它现用资产。旧模型被列为废案不意味着这些共享依赖也已删除。

以下保留是为了现用制作链，不是认可旧外观／旧动作：

| 保留内容 | 当前用途 |
| --- | --- |
| Skin07、ArmSprint06 的原生动作快照 | BeltFeed08 基础动作的制作输入；重新制作更早版本须从归档恢复对应前驱 |
| BeltFeed08 | 现用基础动画与私有骨架来源；旧金属弹箱换弹不恢复 |
| PKMFK19 | Accessories22 可编辑握把姿态依赖 |
| Refine12/201_surface.json | Magazine24 原装弹匣抓握源数据 |
| Video26/LMG201_Video26_Editable.blend | Install30 只读取其原生骨架，不恢复旧枪壳 |
| Detail35 作者代码、Work、贴图、控制件及 UE 母材质 | Repair36 加厚前外皮与现用材质实例的依赖 |

## 当前新模型边界

当前制作链为 **MeshyRetry28 → Refine29 → Install30 → Surface32 → Detail35 局部输入 → Repair36**；布料弹箱为 ClothFeed33，原装弹匣为 Magazine24，ADS 衣物处理为 ADS34。

实际主体仍使用 `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。这是历史包名，内含当前新模型；本次没有把该包当成旧模型移走。当前入口见 [201 发布与恢复说明](../Weapons/lmg201-publication-20260929.md)。新模型已保存但尚未得到最终视觉认可，不能以本次归档检查代替游戏验收。
