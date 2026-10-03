# 祥云符文来源记录

2026-10-02，按用户要求制作唐刀专属祥云符文。

祥云纹样与图标均使用内置 `image_gen` 工具制作，提示词全文见 `imagegen_prompts.json`。使用的云纹为本次生成的原创卷云构图；图标边框参考项目内已接入的腾云游龙改造图标。未使用网络下载图样。

- 原始纹样：`Artwork/CloudRune_Alpha.png`，保留透明 alpha。
- 材质遮罩：`Artwork/TangDao_CloudRune_Mask.png`，从原始 alpha 提取为线性灰度材质通道。
- 图标：`Icons/ue_tang_dao_blade_2_auspicious_cloud_rune.png`，银灰金属框与祥云主印。
- HLSL：`cloud_emission.hlsl`，本次编写的祥云流光分支。
- PBR：分别复用唐刀原装、破锋燕翎、腾云游龙已落盘的材质图和符文发光图节点，三个钢材图集独立保留；不改模型。

内置工具原始输出来源分别为 `exec-5e8847c5-2df9-4925-9c3c-a0251c069659.png` 和 `exec-3253230a-d239-49b9-a43f-71762a465115.png`。游戏正式引用均位于项目目录，不依赖工具缓存路径。
