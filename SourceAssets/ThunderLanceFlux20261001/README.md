# 原创电矛能量洪流源

视觉方向参考用户提供的彗星亚兹勒截图；本目录全部网格、密度数据和HLSL为本次原创制作，没有提取参考游戏模型、纹理或特效。

- Blender背景制作：`Tools/Skills/make_thunder_flux_mesh.py`，导出1m直径／1m长、+Z轴的分段宿主；运行时按实际网格Bounds转换到厘米尺寸。
- 线性密度数据制作：`Tools/Skills/bake_thunder_flux_fields.py`，种子20261001；PNG为无缝1024×256数据图，R翻卷密度、G细折叠、B能量亮脊。
- `FluxCommon.hlsl` 统一沿实际光束方向滚动的坐标；`FluxMask.hlsl` 分层覆盖；`FluxDisplacement.hlsl` 径向翻卷；`FluxFilaments.hlsl` 跳动分叉电丝。
- UE作者：`Tools/Skills/build_thunder_flux_v3.py`，实际保存到 `/Game/Skills/ElectricMagic/ThunderFluxV3`。当前射程翻倍／表现增强50%版本的制作回执在 `Saved/ThunderFluxStrength20261001`，初版回执保留在 `Saved/ThunderFluxV320261001`。束身Translucent提供背景遮挡，窄电丝保留Additive；直径与发光较初版×1.5。

保留 .blend、FBX、PNG、HLSL 与两份production.json供后续调整。没有运行画面测试；细节见 `Docs/Skills/thunder-lance-flux-20261001.md`。
