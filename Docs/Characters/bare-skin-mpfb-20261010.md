# 默认裸手 MPFB 表面与手臂升级

**已否定并回退（2026-10-10）：** 用户实机截图出现严重肘部折叠与扭曲。本页以下为失败版本的历史记录，不是当前基准。85 份网格已从修改前的原始包恢复，20 套制作源、20 个 Blend 和共同母版恢复；自动截面变形、法线重建、物理 UV 改写及其发布入口停用。当前改为 [原模型上的表面重做](bare-skin-surface-rework-20261010.md)。

用户于 2026-10-10 指定使用免费的 MPFB2 / MakeHuman，修整截图中不自然的裸手表面和纹路。沿用 V7 手型与各武器原生骨架，以 MPFB 的解剖结构指导手臂局部修形。

## 来源与制作内容

- 来源：https://github.com/makehumancommunity/mpfb2 。使用 `src/mpfb/data/3dobjs/base.obj`（hm08）和配套权重、关节参考，资产许可证 CC0-1.0；没有把 MPFB 的 GPL 应用代码编入游戏。
- 实际取得所需核心资产，未安装完整 MPFB 插件。下载中断的仓库 ZIP 仅作为原始下载记录；已完整解压的所需文件、许可证和哈希在 `SourceAssets/BareSkinMPFB20261010/External/`、`provenance.json`。
- 使用供体肩、肘、腕关节与上臂/前臂截面，拟合当前体型：目标半径由 70% 供体截面、30% 当前平滑截面组成。母版每侧修整 3117 个手臂顶点，内收不超过 8.5 mm、外扩不超过 4.5 mm，肩部和腕部渐隐。材质 2 的手部顶点固定。
- 在当前原生网格中转移局部位移，保留各武器已有姿态、手指接触修改、原拓扑、蒙皮权重和骨架。原生局部位移上限 1 cm。重建修改区域的平滑法线，保留原有 LOD 数量并重新构建现有 LOD。

## 表面调整

五份现有皮肤父材质原位更新，现有实例继续引用：`M_BareNative_Default`、`M_BareFamily_Arms`、`M_BareFamily_Hands`、`M_M16ThumbNative`、`M_M16ThumbHands`。

- 微表面高度降至原来的 30%，微法线独立于高度调节，幅度乘 0.40。
- 颜色颗粒强度乘 0.32，粗糙度扰动乘 0.25，并随像素覆盖衰减。
- 解剖法线降低并在手腕平滑衔接，指甲保留；保留 M16 专用拇指局部修正。
- 去除裸皮肤材质里残留的布料颜色、编织和布料法线分支；肤色略微加暖，基础粗糙度改为 0.47。
- 继续使用项目现有皮肤贴图；MPFB 在本次提供几何结构参考，并非新增 MPFB 皮肤贴图。

## 坐标修复

部分 FBX 派生网格的附加 UV 保存的是物理坐标，FBX 却同样翻转了 V。此次将其恢复成材质所需的原始坐标；RSH12 还存在一层 UV 索引偏移。Axe/Pickaxe 缺少物理坐标层，使用完整的原生混合绑定逆变换重建。原有解剖 UV0 和武器附加 UV 层保留。

Blender 的公共导出制作源同步预补偿附加 UV 的 V 翻转，避免后续枪械制作再次引入此问题。

## 交付文件与回退

- 新母版：`SourceAssets/BareSkinMPFB20261010/M4_BareArms_MPFB_Editable.blend`。
- 独立供体参考：同目录 `MPFB_hm08_Reference.blend`。
- 20 套原生制作源与 Blend：`SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/`、`Editable/`；原有 Super90 等派生流程继续读取该目录。
- 当前网格快照、稀疏修改、制作记录：新目录中的 `Snapshots/`、`Authored/`、`authoring.json`。
- 实际材质保存记录：`materials_saved.json`；网格逐项保存记录：`Saved/*.json`。制作记录本身不表示资产已经写入。
- 原始 UE 网格包与制作源备份：`Before/Content/`、`Before/SourceAssets/`；父材质副本：`/Game/Characters/ModularOutfit20260924/MPFBSkin20261010/BeforeMaterials/`。

写入从当时的当前网格读取；若磁盘资产在制作期间改变则停止该项，不用旧快照覆盖。中断后已保存项目由回执跳过。主要脚本位于 `Tools/ModularOutfit/mpfb_skin_*.py`；供体拟合在存在本轮备份时自动使用原始母版，避免在已升级母版上叠加同一变形。

## 被否定版本的历史保存记录

可编辑母版、20 套制作源和可编辑 Blend 已保存；五份皮肤父材质已编译并保存；85 / 85 份相关 UE 网格已实际写入并保存，其中 20 份修复了物理坐标层（9 份 FBX V 翻转、9 份 RSH12 层索引偏移、2 份工具缺失坐标）。

材质回执：`SourceAssets/BareSkinMPFB20261010/materials-04.txt`、`materials_saved.json`。网格写入回执：`install-01.txt` 至 `install-08.txt` 以及 `Saved/*.json`；最终批次记录 `saved 85 of 85`。现有编辑器的 PIE 结束后，通过共享桥互斥批次完成保存，没有另开交互编辑器。

未启动游戏、截图、渲染或自动测试，未作运行或视觉验收；最终效果由用户体验。
