# 高地专属剑身Ⅰ：阔锋重刃

版本说明：下文为 V1 初版制作记录。当前游戏已采用[加厚 V2](../BroadbladeThicknessV2_20260922/README.md)，初版源文件继续保留。

选项 `highland_broadblade`，仅 `ue_highland_claymore` 可选。由已接入高地剑原装剑刃制作，保留原有三款剑身Ⅰ选项；不自动改变玩家已安装改造。

## 外形

- 主体设计宽度 11.0 → 10.6 cm，中段边线接近平行，形成宽刃重剑轮廓。
- 剑根至 Z=10.5 cm 保持原形，其上 9.5 cm 平滑展开宽肩。V 形装配接口、护手、握柄、配重不变。
- 中央 24 mm 符文带保留原横向比例，两侧钢刃扩宽；原 UV、原生符文与剑根花纹沿用。扩宽区域的钢材纹理随外侧几何延展。
- 剑脊加厚最多 25%，向切削刃平滑递减；Z=65.5 cm 后逐渐收尖，剑尖仍为 Z=88 cm。
- 使用变形雅可比的逆转置变换原自定义法线，保留原拓扑。

## 数值与接入

沿用接入时 `heavy_spine` 的实际数值：基础伤害 +20%、造成硬直时间 +15%、攻击速度 −25%。独有性为高地剑限定外形；本轮不另加攻击距离、命中半径或专属技能。

运行模型：`/Game/Weapons/HighlandClaymore20260922/Broadblade20260922/SM_Highland_Blade_Broadblade_V1`。

通过 `Content/ColdSteelData/highland-claymore-modules.json` 绑定独立剑刃；通过 `melee-gunsmith.json` 的 `weapons` 限定高地剑。沿用原刀身材质、原生符文功能、符文投射尺寸及攻击端点。使用现有装备实例中的改造保存机制，不修改玩家存档。

UI 图标：`Content/ColdSteelData/AttachmentIcons20260913/ue_highland_claymore_blade_1_highland_broadblade.png` 及同路径 UE Texture。真实部件，1024 × 1024 RGBA 透明、中性灯光、正交侧视、剑尖向左、不镜像。静帧沿用 PBR，未复现 UE 随时间变化的发光效果。

## 可编辑交付

- `HighlandClaymore_Broadblade_Editable.blend`：新剑刃与完整原装剑柄组合；同场景保留原部件作为来源。
- `HighlandClaymore_Broadblade_MenuIcon_Editable.blend`：实际 UI 图标摄影棚。
- `Export/SM_Highland_Blade_Broadblade_V1.fbx`：独立剑刃导入文件。
- `author_broadblade.py` / `authoring.json`：制作脚本与参数。
- `import_and_install.py` / `install_receipt.json`：导入与目录合并记录；变更前目录保留在 `Before/`。

仅资产和数据变更，不需要 C++ 构建。模块目录为进程静态缓存，已载入过旧目录的编辑器需重启；记录见 `editor-refresh.json` / `editor-reopen.json`（如生成）。

未执行自动测试、PIE 或验收渲染；仅生产用途的菜单图标已渲染。由用户测试最终外观与操作。
