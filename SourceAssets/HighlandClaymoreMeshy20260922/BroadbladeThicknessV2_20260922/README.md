# 阔锋重刃：厚度修订 V2

用户反馈宽刃显得过薄，本轮增加真实截面厚度并同步生产用途的菜单图标。

## 制作

由当前实装 V1 `SM_Highland_Blade_Broadblade_V1` 制作。制作前读取源截面：Z=22/35/50 cm 附近中央脊约 8.1/8.0/7.1 mm 厚，外侧宽刃面更薄。

- 中央两面各增加最多 4.2 mm，主段剑脊设计厚度约 15–17 mm。
- 加厚覆盖两侧宽刃面，保留原表面浮雕起伏；每侧半宽约 67% 后过渡到磨刃面，98% 处恢复原切削刃厚度。
- Z=10.5–17.5 cm 平滑接入加厚，安装面保持原形；Z=65.5 cm 后逐渐减少增厚量，末端收尖。
- 仅改变厚度轴 Y，宽度、长度、中央符文横向比例、护手与握柄接口维持 V1。
- 对原稀疏长三角面局部细分，以承载新增截面；原 UV 和面角法线插值延续，法线按变形雅可比逆转置更新。最终 27,870 三角面。

## 游戏接入

原选项 `ue_highland_claymore / blade_1 / highland_broadblade` 引用更新为：

`/Game/Weapons/HighlandClaymore20260922/BroadbladeThicknessV2_20260922/SM_Highland_Blade_Broadblade_ThickV2`

沿用当前阔锋重刃的材质槽，只替换该选项的 mesh 与外观说明。攻击数值、采样端点、符文投射尺寸、存档 ID 均未修改。初版网格与源文件保留。

专属图标同步 PNG 和 UE Texture：`Content/ColdSteelData/AttachmentIcons20260913/ue_highland_claymore_blade_1_highland_broadblade`。沿用初版摄影棚，真实新模型、1024 方形、透明背景、剑尖向左、正交视角。旧 PNG 与目录备份位于 `Before/`。

## 可编辑源与记录

- `Highland_Broadblade_ThickV2_Editable.blend`：加厚剑刃与原装柄部组合。
- `Highland_Broadblade_ThickV2_MenuIcon_Editable.blend`：实际图标摄影棚。
- `Export/SM_Highland_Blade_Broadblade_ThickV2.fbx`：独立剑刃。
- `author_thickness_v2.py`、`authoring.json`：制作脚本、参数和源依赖。
- `source_sections.json`：用于设计厚度的原始 V1 截面数据，不是游戏验收。
- `import_thickness_v2.py`、`install_receipt.json`：导入与窄范围目录更新记录。

本轮资产和目录已导入、保存。为接入打开了编辑器，未启动游戏；无需原生代码构建。未做自测、PIE 或验收渲染，最终外观由用户测试。
