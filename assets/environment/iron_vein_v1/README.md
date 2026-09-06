# 铁矿脉材质 v1

当前使用 `iron_albedo_v2.png`（1254×1254）：按用户要求扩大黑色矿带、加深至炭黑，扩大砖红/红橙锈蚀区域。沿原图分布编辑，目标覆盖约40%灰岩、35%黑矿、25%铁锈；比例为生成提示目标。imagegen 原件 exec-26a466ef-ee15-442b-97ef-f10cf3d0b73b.png。v1 原图保留溯源，物品图标与动画预览随 v2 重渲染。

2026-09-06，按用户授权生成并接入。灰色母岩参考项目现有 `assets/environment/sky_base/stone_voxel_v1/limestone_albedo.png`。

- `iron_albedo.png`：imagegen 原始生成图，1254×1254；完整保留，不放大冒充高分辨率。提示：平铺灰色石灰岩底色、深灰含铁矿带、少量锈褐边缘，平光无高光阴影、无发光晶体。生成原件位于 Codex generated_images 中 exec-4725140d-77f8-4702-a359-1c7ed4df88c2.png。
- `iron.gdshader`：三向投影，按照源模型宽度校准纹理密度；深色矿带粗糙度约 .67、母岩约 .91、锈迹保持哑光。浅浮凸由底色梯度近似推导，非扫描法线/PBR贴图组。边缘平铺为生成目标，未宣称数学无缝。
- `iron_ore_icon.png`：`tests/render_iron_icon.gd` 从现有 boulder_01 模型及此材质渲染的 256×256 透明物品图标。
- 网格与预烘焙碎块复用项目 Poly Haven boulder_01 / rock_09（原资产来源和许可保留在原目录）。不修改原石块贴图。

完整生成提示：Create one seamless square tileable game material BASE COLOR texture, flat orthographic diffuse albedo, no perspective, no lighting, no shadows, no bevels, no text, no borders. Use the reference only as style reference: retain its realistic muted warm-grey limestone matrix and fine stone pores. Transform this into an iron-bearing rock ore vein material: about 65% grey limestone, about 25% dark charcoal grey hematite bands forming irregular branching fractured mineral veins with chunky granular mineral inclusions, about 10% muted reddish brown iron oxide margins. Large readable irregular mineral bands across the texture, natural rock texture at multiple scales. No gold, no crystals, no glowing material, no baked specular highlights. All four edges must tile continuously. Output a single high resolution square albedo texture filling the whole image, suitable for triplanar projection on an existing irregular 3D boulder.
