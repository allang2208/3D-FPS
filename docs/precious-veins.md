# 银矿脉与金矿脉 · 2026-09-06

按用户“相同的”授权沿用现有矿脉采集系统。银矿强调暗灰围岩中的银白矿带和暗色变色边缘；金矿强调灰岩、石英中的金黄矿粒及细脉。均为增强游戏辨识度的艺术组合，不是特定矿床的精确重建。

参考：自然银银白色，可变暗灰至黑色（https://www.mindat.org/show.php?id=3664&ld=1）；自然金可见于热液石英脉（https://zh.mindat.org/min-1720.html）。

imagegen 各生成一张 1254×1254 原始底色图，分别位于 assets/environment/silver_vein_v1/silver_albedo.png 与 gold_vein_v1/gold_albedo.png，未放大。风格参考 copper_albedo.png 的石质颗粒与辨识度。银图原件 exec-e620ec54-3e23-498d-8997-b1536a21fabd.png；金图原件 exec-54dca208-82c0-4842-b58c-47853c1064cb.png。生成目标为平铺平光底色、无烘焙高光阴影；不宣称数学无缝。

银图提示重点：55%暗灰围岩、30%银白颗粒状分叉矿带、15%灰白石英与暗色硫化矿边缘，无铜绿、铁锈或金色。金图提示重点：50%中深灰围岩、20%乳灰石英、25%暖黄金粒和分叉细脉、5%淡赭污迹，保留围岩不变成整片金箔。百分比是提示目标，不是测量结果。

precious_vein_material.gd 复用三向投影与纹理密度规则。按用户追加要求增强稀有金属辨识度：各投影先提取矿带遮罩再混合，矿带金属度 .95、银粗糙度 .16 / 金 .20，局部清漆 .25；围岩约 .9 粗糙度。矿带分别强化冷银色和暖金黄色，保持颗粒变化。没有添加自发光，反光由场景照明驱动。细浮凸仍由底色梯度近似推导，非实测PBR法线。已按同一光照重渲染物品图标和采集动画。

旷野原散石候选 i%22==3 为银矿，i%33==7 为金矿，均要求宽度至少 .65 米；不覆盖原铁铜候选，不额外改变随机数序列与原摆放碰撞。矿镐三击、8块碎片、单次奖励。silver_ore / gold_ore 为普通材料、堆叠999；背包满保留矿脉，原采集存档保持移除。不增加冶炼或建筑配方。

PRECIOUS_PREVIEW=silver 或 gold 可运行 tests/render_scenic_rock.gd --fixed-fps 24 / tests/render_iron_icon.gd，得到实际模型144帧动画及透明图标；PRECIOUS_HARVEST_TEST=silver 或 gold 可运行 tests/test_scenic_rock_harvest.gd 检查正式旷野采集、奖励、相邻实例与存档。
