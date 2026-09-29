# 钢甲护手：全手灰色金属护层

用户要求把甲片下的灰色金属材质覆盖整只手套，不再使用皮革。本轮沿用连续手背／腕部／拇指护甲，只替换原内手套的表面材质。

- 掌心、指腹、指侧、虎口及袖口内手套统一使用原有柔性金属护层的灰色、环纹、粗糙度与金属度配方。
- 从 `steel_gauntlet_finish.material` 的 `flexible_mail` 分支烘焙三张 512 px 可平铺贴图，保留原 0.7 × 0.6 mm 纹理间距。与甲片共用的旧钢材图集不改，避免把钢甲纹理误贴到掌心。
- 材质应用到当前全部原生手模（含 Body）与掉落模型的内手套槽；甲片材质、网格、各级 LOD、骨架、权重和动作不改。
- 三份 Blender 作者源及掉落 FBX 已同步更换材质。作者源备份、旧 UE 材质引用位于 `SourceAssets/MetalGauntlet20260927/SteelGauntletV1/FullMetal20260928/`。
- `build_steel_gauntlets.py` 与 `import_steel_gauntlets.py` 已接入新护层，后续制作、增量导入不会恢复皮革。
- 装备 ID 仍为 `ue_steel_gauntlets`，物品描述同步移除“皮革握持面”。其他皮革手套不受影响。

制作入口：`Tools/ModularOutfit/steel_gauntlet_metal_liner.py`。
材质保存入口：`Tools/ModularOutfit/install_steel_metal_liner.py`。
UE 新材质：`/Game/Characters/ModularOutfit20260924/SteelGauntletV1/FullMetal20260928/M_GreyMetalLiner`。

实际制作与保存结果分别记录于作者目录的 `author-receipt.json`、`install-receipt.json`。不启动游戏、不做自测或预览渲染，静态装备图标沿用原图；实际游戏效果由用户测试。

2026-09-28 13:23 后台导入已完成，退出码 0；新金属护层材质、三张贴图、22 个原生手模（含第三人称 Body）及一个掉落网格已保存。实际回执 `complete=true`。日志为 `Saved/steel-grey-metal-liner-import-20260928.log`。本轮无需 C++ 构建。
