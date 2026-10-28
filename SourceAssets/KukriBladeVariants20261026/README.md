# 尼泊尔弯刀：三款通用刀身外观

> 当前表面版本已转到 [KukriBladeSurfaceV220261026](../KukriBladeSurfaceV220261026/README.md)：更新三款钢材表面、刃口分区、外露刀根纹理与面角法线，并重制标准图标。此批继续作为造型来源；重跑旧脚本后必须最后应用 V2 的表面及图标导入。

用户授权：按三款设计说明生成模型，先不设置数值，接入游戏后由用户测试。

本批使用 Blender 后台制作。三款均已导出 FBX、烘焙 PBR、导入 UE 并保存，再加入尼泊尔弯刀的刀身改造栏；原装选项继续保留。此前概念图生成被工具拒绝，本批依据已保存的文字设计与真实原装网格制作，没有把概念图当作模型。

| 选项 | 稳定 ID | 实际外观 |
|---|---|---|
| 轻型迅刃 | `swift_blade` | 收窄弧腹、双侧浅槽、石墨灰缎面与银色刃口 |
| 厚背重刃 | `heavy_back_blade` | 宽腹、厚实脊面、深灰锻面与宽银色刃口 |
| 百炼均衡刃 | `folded_balanced_blade` | 适中弧腹、银灰百炼流纹、素面刃口 |

## 使用

背包 → 尼泊尔弯刀 → 改造武器 → 刀身。选择三款之一并应用，或恢复原装。复用现有 `gunsmith_parts` 应用、撤销与存档流程，以及主手、双持、副手、预览和掉落装配。

三个选项的 `stats` 均为 `{}`，`effects` 均为 `[]`；没有添加伤害、攻速、耗体、距离或特效加成。刀尖纵向位置、现有碰撞采样元数据与动作保持不变。

## 模型与材质

- 母版：`../KukriModules20261026/Kukri_Modules_Editable.blend`，沿用原 Fab 来源及许可，不扩大源素材再分发权限。
- 坐标、枢轴与接口沿用 `kukri-grip-frame-v1-20261026`。局部 Z ≤ 6.6 cm 区域保持原装位置；原木柄最高约 Z = 5.66 cm，变形在其外侧平顺开始。
- 原装三角面均匀细分后保留源 UV 与插值面角法线，外露刀身按形态变换；法线随变换 Jacobian 转换。每款 10,528 三角面、5,266 顶点，单一材质槽。
- 根部表面混合保留原装钢材，外露表面制作独立 BaseColor、ORM 与切线 Normal，烘焙为 2048 PNG。UE 使用 Substrate FrontMaterial；Blender +Y 法线在导入时翻转绿色通道。
- 新材质和贴图为独立资源；世界贴图保持可流送。网格继承原装刀身的 Nanite 配置，不修改原装材料或其他部件。
- 三张图标由实际模型渲染，使用统一灰阶、水平左向、单件和独立三维金属框。框仅存在于图标作者场景。共享图标按 `blade_1_<id>` 命名，避免后续逐武器复制。

## 入口与文件

- `author_blades.py`：模型变形、法线转换、PBR 烘焙与 FBX 导出。
- `Kukri_Blade_Variants_Editable.blend`：实际接口坐标中的三款可编辑母版。
- `Export/`、`Textures/`、`variants.json`：导出、材质贴图、资产映射与制作记录。
- `render_icons.py`、`icon_grayscale.py`、`Kukri_Blade_Icons_Editable.blend`、`Icons/`：实际菜单图标与可重建作者场景；灰阶助手来自武器技能。
- `import_blades.py`、`import_receipt.json`：后台导入与逐包保存记录，共 18 个资产。
- `publish_variants.py`、`publication_receipt.json`：资产保存完成后合并目录与部署共享 PNG。
- `Before/`：本轮目录修改前副本；不包含或改写玩家存档。

正式资源位于 `/Game/Weapons/Kukri20261020/BladeVariants20261026/`。
正式选项库为 `Content/ColdSteelData/shared-knife-blade-options.json`，由 `kukri-gunsmith.json` 的 `blade_1.options_library` 引用；实际网格在 `kukri-modules.json` 的 `slots.blade_1` 注册。

“通用”指共享选项、图标与制作方式。本批只给尼泊尔弯刀提供安装适配；其他武器仍需按各自实际刀根制作，不会自动套用这组三维网格。

## 落盘与测试边界

后台 UE 导入命令退出码 0，保存回执完成。仅有模型、材质、图标和 JSON 数据变化，无 C++ 变化，因此未重复编译原生目标。没有打开交互 UE 编辑器，没有运行游戏、联机、截图或验收测试；实机表现由用户测试。

## 正式图标接续

三款刀身的最终菜单图由 [KukriFinalIntegration20261026](../KukriFinalIntegration20261026/README.md) 使用本批实际模型图和认可金属母框重新生成并导入。此处 `render_icons.py` 保留为模型素材入口；重跑旧模型／目录发布后，应最后执行新批次的 `deploy_icons.py` 与 `import_icons.py`。
