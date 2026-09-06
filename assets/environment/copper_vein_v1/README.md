# 铜矿脉 v1

2026-09-06，按用户要求参考铜矿及氧化矿物生成。保留现有灰石颗粒，采用赤铜色矿带、黑色氧化边缘和显眼的青绿风化矿斑，与黑红铁矿区分。

矿物依据：赤铜矿 Cu2O 可呈红色，黑铜矿 CuO 呈黑色；绿色参考孔雀石等次生铜矿物，不把绿色标成纯氧化铜。参考 https://www.mindat.org/element/Copper 、https://www.mindat.org/min-1172.html 、https://www.mindat.org/min-2550.html 、https://www.mindat.org/JT1-WP5 。本材质是便于游戏辨识的艺术组合，并非特定矿床复原。

`copper_albedo.png` 为 imagegen 生成原图 1254×1254，未放大。原件 exec-a41dd76c-bcd7-46e1-adfe-75768853399b.png，参考图为 iron_albedo_v2.png（只参考石质细节和辨识度）。提示要点：单张平铺平光底色；40%灰岩，25%孔雀石绿/青绿次生矿物，20%赤铜色矿带，15%黑色氧化边缘；粗细两级矿带与微裂纹，不发光、无阴影文字。平铺为生成目标，未宣称数学无缝。

`copper_vein_material.gd` 复用三向投影与浅浮凸着色器，保持铁矿默认参数不变；铜矿单独设置低金属度 .06，氧化表面保持哑光。浮凸来自底色梯度近似，不是实测法线贴图。网格复用 Poly Haven boulder_01 / rock_09，原来源与许可保留在原资产目录。

`copper_ore_icon.png` 是现有不规则 boulder_01 实际模型与此材质的透明渲染，256×256。通过 COPPER_PREVIEW=1 运行 tests/render_iron_icon.gd 可重现。
