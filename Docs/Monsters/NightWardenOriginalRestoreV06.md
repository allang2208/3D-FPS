# 守寝者恢复原始模型 V06

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

2026-10-16 用户否定当前角色的整体形变，要求先撤下全部衣物布料，恢复最初导入的模型，优先完成基础模型导入。本轮暂停继续迭代衣物和移动动画。

## 恢复输入与范围

- 用户原件：`C:/Users/allan/Downloads/Meshy_AI_Character_output (5).glb`。
- 工程原件：`SourceAssets/NightWarden20261015/Input/NightWarden_Meshy_Original.glb`，两者 SHA-256 均为 `b654dbc3416fe737627649ed19e5e35800da0e46b8ed0bb3b43b89da4d62fa3c`。
- 直接从原 GLB 重新准备：145,849 个源顶点、198,386 个三角形、45 根原骨骼、约 1.7 米原始高度。保留完整身体网格、原 UV、原权重和骨骼父链，不采用之前为衣物遮挡裁切的身体，不采用新增手指／道具骨或重新分配的蒙皮。
- 原 GLB 的三张嵌入 PNG 直接抽取：颜色、OpenGL 法线、金属／粗糙度。UE 为法线设置绿通道翻转，粗糙度使用 G、金属度使用 B；保持原 double-sided 材质设定。
- 从当前显示入口撤下外套、裤子、鞋靴、线缝、五金、钥匙、手电和所有旧动画。已有制作源与旧资产保留作为历史恢复材料，当前基础模型使用独立 Skeleton。
- FBX 使用 `FBX_SCALE_UNITS` 声明米单位，由 UE 转为厘米；模型本身保持原比例。只交付原始姿态，不增加动画、布料或物理模拟，不再制作额外 LOD。

## 状态与路径

原始模型作者源、FBX、三张贴图、UE 材质、独立骨骼网格及 Skeleton 均已实际保存。原 `BP_NightWarden` 已切换到新身体模型，清空旧动画、材质覆盖，关闭动画后处理与物理模拟，以原始参考姿态显示。胶囊及模型位置按原 1.7 米身高恢复。

实际回执为 `V06Original/Records/ue_delivery.json`，状态 `original_model_and_entry_saved`、`complete=true`，共保存 7 个资源包。最终入口保存通过后台 commandlet 完成，退出码 0。模型导入包围盒高度约 170 cm。用户可在原 F6 守寝者入口重新生成；菜单文字仍沿用原有名称，当前显示模型没有衣物和手电。

- UE 模型：`/Game/Monsters/NightWarden/V06Original/SK_NightWarden_Original`。
- UE 骨架：`/Game/Monsters/NightWarden/V06Original/SK_NightWarden_Original_Skeleton`。
- 入口：`/Game/Monsters/NightWarden/BP_NightWarden`。

- 作者源：`V06Original/Authoring/NightWarden_Original_Restored.blend`。
- 导出：`V06Original/Exports/SK_NightWarden_Original.fbx`。
- 原贴图：`V06Original/Textures/`。
- 制作合同：`V06Original/Records/source_manifest.json`。
- 制作入口：`Scripts/prepare_original_v06.py`。
- UE 导入与同批入口替换：`Scripts/import_original_v06.py`、`Scripts/activate_original_v06.py`、`Scripts/original_background_v06.ps1`。`-Stage Activate` 可继续已保存模型的入口切换，无需重导全部资源。

本轮按恢复要求完成制作和接入，不追加渲染、姿态采样或游戏测试。此前 V02 的局部数据对齐不代表用户认可；原始自动蒙皮的动画质量也未在本轮作出合格结论。
