# 裤子与鞋靴装备

三款物品接入当前 Jason 身体：

| 名称 | 定义 ID | 装备槽 | 背包占格 |
| --- | --- | --- | --- |
| 牛仔裤 | `ue_jeans` | 裤子（15） | 2×3 |
| 工装裤 | `ue_cargo_pants` | 裤子（15） | 2×3 |
| 休闲鞋 | `ue_casual_sneakers` | 鞋靴（13） | 2×2 |

在开发面板的物品目录“装备”中选择对应物品并生成，随后使用现有右键装备或拖拽。裤子槽追加在原有槽之后；旧槽编号、背包槽、武器槽及存档定位不移动。已有玩家存档没有被主动修改。

穿戴网格、独立身体覆盖底网格、掉落网格与图标显示网格位于 `/Game/Characters/ModularOutfit20260924/LowerBodyEquipment20261003`。当前身体源资产和动画保持原路径；模块化衣服系统按配置使用新的身体覆盖底网格。裤子与鞋仅绑定世界身体，未增加第一人称武器手臂部件。

模型保留源衣物的拓扑、UV 和 PBR 材质，使用 Jason 骨架重新适配位置与蒙皮。牛仔裤裤脚为休闲鞋留出外侧空间。三款穿戴资产各有三级 LOD。常规骨骼网格通过 Leader Pose 跟随身体，不在运行时实例化 MetaHuman 服装工具或布料模拟。衣服和下装的身体覆盖共享原有分区规则，脱下装备后恢复对应皮肤。

图标使用与穿戴模型一致的显示网格及原生 UE 材质，掉落使用独立静态网格。物品定义位于 `Content/ColdSteelData/items.json`；外观配方位于 `Content/ColdSteelData/modular_outfits.json`。生成记录位于 `SourceAssets/LowerBodyEquipment20261003`，制作脚本位于 `Tools/LowerBodyEquipment`。

来源由用户提供并授权用于本项目：

- [MetaHuman Jeans](https://www.fab.com/listings/07dc895c-7402-411c-a74a-e1c47b33ac68)
- [MetaHuman Cargo Pants](https://www.fab.com/listings/586d2fd4-9ae9-4d91-9e61-2a362008d052)
- [MetaHuman Casual Sneakers](https://www.fab.com/listings/7e58d5c5-5666-4ab2-9c4e-011eeaba3c07)

本地源包及原始 Manifest 记录在 `provenance.json`。派生模型与贴图仅落在本地项目，没有上传或单独分发；使用遵循对应 Fab 获取许可。

按用户规则未主动运行游戏、进行动作/穿模/存档测试或制作验收截图。实际穿戴效果、切换和存档由用户测试。资产保存、构建与生产图标输出分别记在该制作目录的日志中。
