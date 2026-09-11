# 强化石紫色魔法矿石材质

用户要求给现有强化石模型增加紫色魔法矿石材质。本次只调整 UE 材质，不重新启动已暂停的 5080 建模任务。

`/Game/Items/EnhancementMaterials/enhancement_stone/SM_enhancement_stone` 绑定独立材质 `M_enhancement_stone_amethyst`。原材质 `M_enhancement_stone_0` 和原始贴图保留。

- 深紫色岩石基底保留纹理亮度变化；原冰蓝矿脉通过颜色差遮罩改为紫水晶色。
- 矿脉有低强度局部自发光，岩石与晶体使用不同矿物反射比例；原有烘焙法线、粗糙度、几何与碰撞不变。
- 可编辑构建脚本：`Tools/AssetPipeline/apply_amethyst_stone.py`。常规材料导入脚本末尾应用此变体，避免重导入恢复为旧色。
- Delivery GLB/Blender 保留原始母版配色；本次紫色为 UE 材质变体，以 UE 实际渲染为准。

导入标记：`AMETHYST_STONE_MATERIAL_PASS`。运行日志：`Saved/AmethystStoneRuntime.log`；实际游戏近景另存为 `Saved/AmethystStoneInGame.png`。

实际运行验收：AmethystStoneAudit_20260911b，27 项通过、0 失败，无材质编译回退。已查看最终 UE 截图，紫色基底与矿脉可见。

![UE 紫色强化石](../../Saved/AmethystStoneInGame.png)
