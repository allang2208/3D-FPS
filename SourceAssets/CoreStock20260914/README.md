# 镂空轻型枪托（原名核心枪托）

当前显示名为“镂空轻型枪托”，属性为后坐力控制 +10%、枪械稳定性 +5%，ADS 瞄准时间无修正；内部 ID 仍为 `core_stock`。M4、AKM、QBZ191 的目录数据和 `update_catalog.py` 已同步更新，模型沿用用户指定的 Meshy 版本。本次仅修改目录数据，无需原生编译；重新进入游戏加载新目录，未运行测试。

## 当前 Meshy 替换轮次

用户于 2026-09-14 指定新的 Meshy ZIP 替换核心枪托外观，说明和当前状态见 [Meshy0914005605/README.md](Meshy0914005605/README.md)。本文件下文记录上一版 5080 前段修整的历史交付，不代表新 Meshy 版本的编译或测试状态。

用户明确要求本模型作为新的“核心枪托”，撤回上一轮替换现有骨架枪托的做法，并修整前段突出的不规则凹凸面。

## 身份、属性与恢复

新配件 ID 为 `core_stock`，显示名为“核心枪托”，加入 M4、AKM 和 QBZ191 的 stock 目录。保留原有 `skeleton` 骨架枪托和 `qr_performance` 高性能后托各自的条目、属性及存档身份。

| 核心枪托属性 | 数据 |
| --- | --- |
| ADS 瞄准速度降低 10% | 目录存储的是耗时增量：`ads_percent = 1 / 0.9 - 1 = 0.11111111111111116` |
| 后坐力降低 15% | `recoil_mult = 0.85` |
| 枪械稳定性增加 10% | `stability_mult = 1.1` |

单独装配核心枪托时，开镜耗时乘以 1/0.9。其余叠加遵循现有枪匠公式，稳定性继续由 WeaponHandling 转换为枪械反馈和回稳参数；没有添加另一套数值逻辑。

原骨架枪托的源码引用恢复为：

- M4：`/Game/Weapons/ReferenceStock5080/SM_SkeletonStock`
- AKM：`/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock`
- QBZ191：`/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_skeleton`

上一轮只切换了引用，没有覆盖上述原资产，因此本轮恢复引用即可。现有存档中的 `skeleton` 继续代表原骨架枪托；不自动改成新核心枪托。

## 前段修整

以 5080 seed 91379 的上一版游戏低模为制作来源，局部切除前端约 4 cm 的不规则外壳、粘连突出和下挂细节。新增规则的圆滑护套、连续肩部曲面、口沿倒角、下方连接片及圆形销钉，保留主体、主要镂空、托板和逐枪挂点。

前段使用实际新几何及独立材质，不继续采样旧的凹凸结构法线。前护套为平整聚合物；连接片、销钉和转接环采用对应枪型金属涂层。转接环侧面使用平滑法线，端部保留平面。未修改的主体区域保留原 UV、角点法线及 4K 烘焙贴图。

这些是制作内容，尚未作本轮视觉或游戏验收，不把旧截图作为修整后的效果图。

## 文件

- `CoreStock_FrontParts_Editable.blend`：前段与保留主体分件可编辑源。
- `CoreStock_Canonical_Editable.blend`：合并的标准空间模型，包含隐藏来源对象。
- `{M4,AKM,QBZ191}/CoreStock_Game_Editable.blend`：逐枪版本。
- `{M4,AKM,QBZ191}/SM_CoreStock.fbx`：UE 导入文件；同目录 `CoreStock_Game.glb` 为通用交换文件。
- `Textures/`：保留主体的 4K BaseColor、MetalRough 和 Normal。
- `Before/`：本轮修改前的目录数据及源码快照，不用于全文件覆盖并行修改。

作者导出面数（含转接）：M4 46,206；AKM 47,422；QBZ191 46,582。来源与操作分别记录在 `front_authoring.json`、`variant_authoring.json`、`catalog_authoring.json`。

`rebuild_front.py` 制作前段；`prepare_authors.py` 从保留的上一轮工具生成本地作者/导入脚本；`author_variants.py` 导出逐枪版本；`update_catalog.py` 只更新三把步枪中的独立条目；`import_assets.py` 导入新资源。

## 接入状态

三枪新资源已导入并保存：`/Game/Weapons/CoreStock20260914/{M4,AKM,QBZ191}/SM_CoreStock`。本轮使用已有纯资源导入宿主完成导入，进程退出 0；`import_results.json` 是保存回执。Config/DefaultGame.ini 增加此资源目录的打包条目。

SkeletonStockVisual.cpp 增加独立 `core_stock` 分支，并恢复 `skeleton` 的原路径；QBZ191Attachments.h 同样区分两种 ID。角色、改造预览、库存图标和地面武器继续使用共同装配入口。

用户保存并关闭编辑器后，已通过 `Tools/Build/Build-Editor.ps1` 完成原生模块及依赖编译，结果为 `Succeeded`，进程退出 0。记录见 `build_editor.log` 和 `integration_status.json`。重新打开项目即可加载本轮编译的原骨架枪托引用和独立核心枪托分支。

遵守用户规则，本轮不追加测试、验收、游戏启动或效果渲染。模型外观、装配和数值表现由用户测试。
