# 法杖副手与晶辉照明图标

2026-09-28：接入法杖主手＋副手手枪，以及 G 键特殊功能。

`staff_light_cold_steel.png` 是本次使用内置 imagegen 生成的透明 PNG 源图，正式副本为 `Content/ColdSteelData/Skills/staff_light_cold_steel.png`。沿用现有快捷栏 PNG 加载方式，无需 UE 资产导入。`Tools/UI/prepare_cold_steel_skill_icons.py` 保留该源图的恢复入口。

生成提示：单个方形、透明背景的幻想 FPS 快捷栏图标；粗糙木杖顶端与麻绳固定的长形白水晶，内部暖白金色照明，数道短光芒，冷钢风格、清晰切面，适合 48 像素显示。无边框、无底板、无文字、无数字、无水印，只画杖头。

完整提交提示（内置 imagegen，transparent_background=true）：

> Create one production-ready fantasy FPS ability hotbar icon: apprentice wooden staff crystal illumination. Square 1:1 image, isolated on genuinely transparent background. A large elongated faceted quartz crystal, ivory white and warm pale gold internally lit, mounted on the short visible upper tip of a rugged dark wooden staff tied with a simple hemp cord. Crystal is the dominant readable silhouette, tilted slightly to the upper right, with four to six crisp short rays of warm light radiating out and a restrained small halo. Cold steel dark fantasy game UI illustration, detailed carved/faceted 3D look with clean graphic readability at 48 pixels, strong contrast, desaturated grey wood, restrained warm gold light. Centered close-up, generous transparent margins, no frame, no border, no background plate, no text, no letters, no numbers, no watermark. Only the crystal and short staff head, not an entire staff. Save as a transparent PNG game icon.

图标只用于武器特殊功能。没有改动默认水晶模型或材质，V34 回退保持生效。未运行游戏或进行验收渲染。
