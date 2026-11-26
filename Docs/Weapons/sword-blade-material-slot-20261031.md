# 剑身材质与符文栏拆分（2026-10-31）

**最新状态：** 用户已确定整套材质数值，后续以 [剑身材质属性定稿](sword-blade-material-stats-20261031.md) 为准。下文零属性为最初外观阶段的历史记录。

本轮按用户确认只做外观。符文长剑新增原厂、折叠纹钢、玄铁、秘银；四项均无属性与特殊效果。其他五把剑保留空白材质栏，后续独立制作。

后续已追加“大马士革钢”特殊材质，仍只对符文长剑开放、无属性；制作与恢复步骤见 [大马士革钢接入记录](damascus-blade-material-20261031.md)。

另已追加“陨铁”特殊材质，范围与零属性规则一致；制作与恢复步骤见 [陨铁接入记录](meteoric-iron-blade-material-20261031.md)。

## 栏位与数据

- 顺序：剑身Ⅰ → 剑身材质 → 符文 → 护手 → 握把 → 配重锤。
- 原 `blade_2` 仅将显示名称从剑身Ⅱ改为符文；内部 ID 与现有符文选项不变，原厂显示为原厂符文。
- 新增 `blade_material`。原厂 ID 沿用目录的 `false`，模块数据对应 `factory`；原厂使用模式 0，原有材质输入保持原值。
- 折叠纹钢 `folded_steel` / 模式 1：银灰金属、细密层叠锻纹。
- 玄铁 `dark_iron` / 模式 2：深灰黑金属、细拉丝。
- 秘银 `mithril` / 模式 3：银白金属、细腻柔光。
- 三款选项均为通用外观风格，本轮只对 `ue_rune_sword` 开放；不提前赋予属性。
- 寒霜晶剑、高地双手剑、唐刀、玄敕镇岳、斩马刀的该栏选项为空，显示“暂无材质”与“暂无可用剑身材质。”。

目录位于 `Content/ColdSteelData/melee-gunsmith.json`；材质模式位于 `Content/ColdSteelData/rune-sword-modules.json`。后者的 `blade_material` 是表面配置，不加入几何替换槽列表。

## 渲染接入

`ModularSwordVisual.cpp` 将材质选择加入外观缓存键，在原生金色/银色符文材质选定后，仅对剑身组件设置 `BladeFinishMode`。护手、握把等共享材质实例保持默认模式 0。现有装备、改造草稿和保存流程继续按槽位键携带选项。

两套已有主材质均已添加表面分支并实际保存：

- `/Game/Weapons/AzureRunesword20260913/M_AzureRunesword`
- `/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold`

分支在原有湿润处理之前调整底色、粗糙度、金属度及细微法线。保留原始法线、符文遮罩和发光输入；金色与银色符文实例仍使用其原有父材质。局部坐标经顶点插值传入像素着色，细纹按屏幕导数衰减。显式 Substrate 输出沿用完整 PBR 输入。

## 图标与制作入口

已保存 5 个图标 Texture2D：`blade_material_folded_steel`、`blade_material_dark_iron`、`blade_material_mithril`、`category_blade_material`、`ue_rune_sword_blade_material_false`，目录为 `/Game/ColdSteelData/AttachmentIcons20260913`。

三款新图标以现有符文长剑框架为参考，经内置图像生成工具制作；原厂与栏位沿用现有剑身图。完整提示词记录在 `SourceAssets/SwordBladeMaterials20261031/icon-prompts.json`。

同目录保留 `install_catalog.py`、`install_materials.py`、`install_icons.py`、修改前备份与导入回执。若以后重新生成基础主材质，应在基础制作结束后再次运行 `install_materials.py` 恢复本轮表面分支。

## 交付边界

材质编译和资产保存属于本轮必要制作步骤，结果见 `material-receipt.json`、`icon-receipt.json`。源码构建结果见同目录 `build-receipt.json`。按用户规则未进行额外静态检查、PIE、游戏运行、渲染截图或验收；最终画面与交互由用户测试。
