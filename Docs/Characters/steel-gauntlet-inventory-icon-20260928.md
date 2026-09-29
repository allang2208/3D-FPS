# 钢甲护手装备栏图标同步

按 `skills/ue5-item-asset-workflow/references/glove-inventory-icons.md` 和 `non-weapon-items.md` 的离线装备出图规则更新。

全金属护层改造已同步 Blender 作者源，但目录 PNG 仍是此前的皮革边缘版本。原出图入口使用 512 px、88% 填充和 AgX，本轮统一为手套专项标准：单只空手套、自然分指、竖向正交镜头、320×320 RGBA 透明底、轮廓居中、主轴约占 91%、Standard 视图变换及生产贴图来源的曝光校准。

## 本次产物

- 活动图标：`Content/ColdSteelData/Icons/MetalGauntlet20260927/ue_steel_gauntlets.png`。
- 作者图标同步更新：`SourceAssets/MetalGauntlet20260927/SteelGauntletV1/ue_steel_gauntlets.png`，防止后续导入覆盖回旧图。
- 独立编辑场景及出图回执：该作者目录下 `InventoryIcon20260928/SteelGauntlet_InventoryIcon.blend`、`delivery.json`。
- 原 PNG 与原生成脚本保存在 `InventoryIcon20260928/Before/`。
- 出图日志：`Saved/steel-gauntlet-icon-20260928.log`。

独立入口为 `Tools/ModularOutfit/render_steel_gauntlet_icon.py`，只读当前 `SteelGauntlet_Icon.blend`，使用其中的 `GreyMetalLiner_Baked` 与 `SteelGauntlet_Baked` 生产材质。`build_steel_gauntlets.py` 的图标阶段也复用这个入口，避免重新生成后回到旧尺寸和曝光。

最终像素尺寸 320×320，主体填充 91.25%，轮廓中心为 (0.5, 0.5)。本轮没有重新导出或导入手模、掉落 FBX、动画及 UE 材质，也没有修改防御／换弹／拉弓数值。

装备栏和背包都沿用原 `ue_icon` 路径读取 PNG，不需要新 UE 纹理资产或 C++ 构建。当前界面有纹理缓存，下次进入游戏读取新版；没有启动 UE 或进行游戏验收。
