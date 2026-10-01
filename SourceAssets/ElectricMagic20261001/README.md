# 电系魔法图标与素材来源 · 2026-10-01

两个正式图标由内置 `image_gen.imagegen` 分别生成，原始输出保存在 `Icons`，实际运行副本在 `Content/ColdSteelData/Skills`。写实冷钢方向：石墨暗底、细旧银框、清晰电系主体；雷暴为多层暗云与蓝紫落雷，雷枪为笔直白蓝核心光束与加速能量环。完整英文提示词与输出路径见 [manifest.json](manifest.json)。本轮未主动预览或验收。

电系音效取原项目 `public/assets/sounds/skills/lightning-1.mp3` 与 `lightning-2.mp3`。本轮复用已经落盘的 `SourceAssets/Lightning20260920/S_LightningCast1.wav` 和 `S_LightningCast2.wav`，引擎声音副本另设空间衰减／并发，不改原声音资产。

云使用本机合法导入的 Normandy 风暴云遮罩，经已有 Blizzard StormV2 材质复用；雷枪使用已安装的 Dr.Game Free Spline VFX 专用副本。Epic Niagara Examples仅作为作者模板。法术自身的电花／电丝／环材质为程序化新作。

制作入口 `Tools/Skills/build_electric_magic_assets.py`，只写 `/Game/Skills/ElectricMagic`；PNG恢复入口为 `Tools/Skills/restore_electric_icons.py`。实际保存11份引擎资产，回执在 `Saved/ElectricMagic20261001/asset-authoring.json`；两PNG已实际复制，不是待执行导入清单。所有Fab母版、WAV和本机uasset保留本机，未进行公开再分发。
