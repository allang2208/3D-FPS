# 大马士革钢特殊材质（2026-10-31）

**最新状态：** 已按用户定稿接入暴击率+10%、暴击伤害+20%、攻击体力消耗+10%；见 [材质属性定稿](sword-blade-material-stats-20261031.md)。下文零属性为最初外观阶段的历史记录。

用户确认本轮仅对符文长剑开放，其他五把剑继续保留空白材质栏。沿用上一轮纯外观设定，不增加属性或战斗特效。

## 目录

- 栏位：剑身材质 `blade_material`。
- 选项：大马士革钢 `damascus_steel`。
- 分组：特殊改造 `special`；公共分级函数按槽位与选项 ID 识别，后续武器适配可复用同一项。
- 当前适用：`ue_rune_sword`。
- `stats`、`effects`、`special_effects` 均为空；不以“特殊改造”分组虚构绿色机制说明。
- 短说明：银亮与深灰钢层交织，呈现流动水纹与细腻蚀刻。

## 参考与表面制作

研究参考为生产商公开的花纹钢资料：

- [Damasteel 纹路原理与类型](https://damasteel.se/knowledge-hub/our-patterns/)：扭绞、压纹与蚀刻后的花纹表现。
- [Björkmans Twist 实物与正反面样本](https://damasteel.se/steel-and-patterns/all-patterns/bjorkmans-twist/)：不规则层纹和自然纹理走向。
- [DS93X 数据表](https://damasteel.se/wp-content/uploads/2024/07/240712-data-sheet-damasteel-martensitic-damascus-ds93x.pdf)：不同钢层的明暗蚀刻响应、表面处理与光泽的关系。

游戏表面为自行编写的程序化材质，不导入网页图片作为游戏贴图，也不复制某款商标花纹。模式 4 使用局部空间水波与扭绞层纹，银亮层和深灰层分别对应不同粗糙度；只加入浅法线起伏，保留原始结构法线。纹理随剑移动，按屏幕导数过滤过细条纹。

在两套既有主材质的表面分支内增加模式 4，原厂及模式 1–3 保留原代码。原生符文遮罩、金色／银色发光、湿润处理与 Substrate 输出沿用现有连接；运行时仍由剑身组件设置 `BladeFinishMode`，不改护手、握柄或配重锤。

- `/Game/Weapons/AzureRunesword20260913/M_AzureRunesword`
- `/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold`

## 交付与重建

作者目录：`SourceAssets/DamascusBladeMaterial20261031`。

- `install_catalog.py` 增量合并目录与模式，不覆盖其他改造。
- `install_materials.py` 在已有表面分支上添加大马士革钢；修改前资产备份位于 `BeforeAssets`。
- `install_icon.py` 导入共享图标 `blade_material_damascus_steel`，使用 UI 纹理组、Editor Icon 压缩、sRGB、Never Stream。
- `damascus_steel.png` 为内置 imagegen 基于本项目既有剑身图制作的灰阶金属框图；提示词与参考路径在 `icon-prompt.json`。这张图是改造图标，不是游戏实拍截图。
- `install_assets.py` 顺序执行材质和图标保存；结果分别记录于 `material-receipt.json` 与 `icon-receipt.json`。
- `build.ps1` 完成公共特殊分组代码的后台构建，结果见 `build-receipt.json`。

若重新制作上一轮基础表面资产，应先完成 `SwordBladeMaterials20261031` 的基础安装，再运行本目录的目录及资产安装入口恢复此项。未运行游戏、PIE、渲染截图或额外验收；用户自行测试实际效果。
