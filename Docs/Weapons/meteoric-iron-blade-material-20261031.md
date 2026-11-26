# 陨铁特殊材质（2026-10-31）

**最新状态：** 已按用户定稿接入物理伤害+15%、韧性伤害+25%、近战攻击速度-10%；见 [材质属性定稿](sword-blade-material-stats-20261031.md)。下文零属性为最初外观阶段的历史记录。

接续用户认可的方案制作。当前仅对符文长剑开放；其他五把剑仍为空白材质栏。纯外观、零属性。

## 改造目录

- 栏位：剑身材质 `blade_material`。
- 名称／选项 ID：陨铁 `meteoric_iron`。
- 分组：特殊改造；公共分级函数识别该槽位与 ID，后续适配可复用。
- 当前兼容：`ue_rune_sword`。
- 模式：`BladeFinishMode = 5`。
- `stats`、`effects`、`special_effects` 均为空。
- 说明：深灰剑面交织银白晶纹，细腻金属光泽随角度变化。

## 表面表现

造型参考 [NASA 的铁镍陨石晶纹照片与说明](https://science.nasa.gov/photojournal/iron-nickel-meteorite-from-texas-with-triangle-pattern-texture/)。游戏采用魏德曼花纹的艺术化表现：深枪灰底色、三组斜向交错的银灰晶带、三角晶区与晶带内细抛光线。网页照片仅用于参考，不作为游戏贴图导入。

程序化纹理使用剑身局部坐标，随剑移动。不同晶带有独立的底色、粗糙度与浅法线偏移，使分区高光随光照与观察方向变化。按屏幕导数过滤晶带和抛光细纹，保留原有结构法线。

在以下两套已有主材质的模式节点中添加模式 5；模式 0–4 的代码原样保留，湿润、原生符文遮罩、发光与 Substrate 接线继续使用已有配置：

- `/Game/Weapons/AzureRunesword20260913/M_AzureRunesword`
- `/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold`

运行时沿用 `ModularSwordVisual.cpp` 的材质模式应用和外观缓存键；只修改剑身组件，不修改护手、握柄、配重锤或战斗公式。

## 制作与交付

作者目录：`SourceAssets/MeteoricIronBladeMaterial20261031`。

- `install_catalog.py`：增量合并改造目录与模块模式，保留其他选项。
- `install_materials.py`：在现役主材质中追加模式 5，保存前备份至 `BeforeAssets`。
- `install_icon.py`：导入共享图标 `blade_material_meteoric_iron`，使用 UI 纹理组、Editor Icon 压缩、sRGB 和 Never Stream。
- `install_assets.py`：顺序运行材质与图标保存。
- `meteoric_iron.png`：内置 imagegen 制作的灰阶金属框改造图标；提示词与参考路径见 `icon-prompt.json`。该图不是游戏实拍截图。
- `material-receipt.json`、`icon-receipt.json` 与 `build-receipt.json` 分别记录实际资产保存及后台源码构建结果。

重建顺序为基础 `SwordBladeMaterials20261031` → `DamascusBladeMaterial20261031` → 本目录，分别应用目录和材质入口。按用户规则未启动游戏、PIE、截图渲染或额外验收，实际画面与交互由用户测试。
