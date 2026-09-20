# Rustic 矿镐模型与双手持握

攻击动作现已继续制作独立的双手举顶下砸方案；新的时序与接入状态见 [矿镐举顶下砸](pickaxe-overhead-attack-20260919.md)。下文的 Swing / HitRecover 0.68 / 0.44 秒是首轮模型替换时的源片段说明，不作为后续运行时攻击节奏。

用户指定模型：`D:/FPS3D/资产/模型/Meshy_AI_Rustic_Mountaineering_0919083808_texture.glb`。
本轮制作模型替换、双手待机、装备和奔跑。采矿判定、材料产出、7/F7 操作和 2×3 背包占格沿用现状。

## 模型与贴图

- 完整原始 GLB 留在 `SourceAssets/RusticPickaxe20260919/Original/`；用户提供的 Meshy 资产不视为已获公开再分发许可。
- 按 84 cm 总长适配，保留原轮廓、UV 和原始编码的 PBR 图片。第一人称目标约 96,000 三角面，世界物体 32,000，远处 LOD 8,000 / 2,000；确切导出面数见 `model.json`。
- glTF 的 MetallicRoughness 图使用 G 通道粗糙度、B 通道金属度。法线图在 UE 翻转绿色通道；颜色 sRGB，数据贴图线性。
- 材质、世界模型、手模及六个动作使用独立的 `/Game/Items/ProductionTools/RusticPickaxe20260919/` 路径。原矿镐资产保留。
- 编辑源：`RusticPickaxe_Fitted_Master.blend` 和 `RusticPickaxe_TwoHand_Editable.blend`；FBX 与贴图分别在同目录 `Export/` 和 `Textures/`。

## 动作制作

读取实际参考 `Axe_ThumbFix_Idle_Equip_Editable.blend` 的 H4 双手动作：左低右高、斧刃向前，低位双手抬起，末段回稳。使用当前 Manny 手臂、骨架 rest、整段前臂及辅助骨关系。

新镐柄较细，左右握点按各自掌心段的截面中心、半径和轴向适配，保持掌面原有接近方向。四指只在原抓握上增加有限弯曲；不缩放骨长，不移动指骨，不独立追逐指尖。拇指根沿用修正后的姿态，末两节适量闭合。参数记录于 `authoring.json`。

| 动作 | 时长 | 制作内容 |
| --- | --- | --- |
| Idle | 3.00 s 循环 | H4 双手持握与呼吸，按新镐柄适配 |
| Equip | 0.48 s | 从下方抬起，0.40 s 到达后轻微收稳，结尾接 Idle |
| Walk / Run | 0.80 / 0.64 s 参考循环 | 双手与工具共同绕握点中部摆动，保留固定接触 |
| Swing | 0.68 s | 沿用旧矿镐挥击参考，沿柄调整支撑位置，首尾接新握姿 |
| HitRecover | 0.44 s | 沿用旧回收节奏，双手共同支撑并回到新 Idle |

Swing 的接触仍在 0.24 s；本轮没有给矿镐移植伐木斧的蓄力、停帧或相机冲击。挥镐与回收的双手衔接用于保证新持握连续，不是新的攻击方案。

所有剪辑以 150 Hz 导出。待机／装备／挥镐／回收使用正式序列。奔跑正式运行时使用 Idle 加 `UpdateTwoHandLocomotion`，从角色脚步获取相位并按速度淡入，防止起跑、停步和动作间切换时跳变。Walk/Run 的 FBX 和 UE 序列作为同套持握的可编辑步态参考，不在运行时重复叠加。

矿镐跑步位移幅度：前后 0.55 cm、左右 2.3 cm、上下 1.35 cm，旋转幅度约 1° / 1° / 2°。参数在 `ProductionToolComponent.h` 的 Pickaxe Locomotion 组，斧头现有参数保留。装备或挥镐时收起步态，命中后不继续叠加摆动。

## 接入状态

模型、动作和 C++ 接入源码已完成。导入脚本为 `Tools/Production/import_rustic_pickaxe.py`，只在所有新包保存后更新矿镐的世界模型、手模、动画前缀三个目录字段；现有存档的同三字段由原有 `NormalizeProductionState` 刷新。

编辑器关闭后已完成正式构建与新资产导入，目录三个表现字段已切换。构建记录：`Saved/BuildEditor/build-20260919-213555.log`；导入记录：`Saved/Logs/RusticPickaxeImport20260919.log` 和 `SourceAssets/RusticPickaxe20260919/import_receipt.json`。

没有运行自测、实机测试或预览渲染，外观和手感由用户测试。
