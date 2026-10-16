# 鸭舌收束器

本版外观已被用户否定并退役。当前使用相邻 `Super90DuckbillV2_20261016` 目录中从零重建的双唇模型、图标与导入流程；不要使用本目录安装脚本覆盖活动资产。本目录保留历史制作记录。

用户要求继续制作散弹枪鸭舌收束器，使散弹沿水平方向射出，并确认额外效果为腰射散布减少 25%。本次接入 SUPER90，沿用前面三款枪口配件的特殊改造分类。

## 游戏效果

- 配件 ID：`shotgun_duckbill`，枪口槽。
- 多弹丸射击改为横向扇形分布，腰射和 ADS 都生效。每颗弹丸占据一个横向区间，区间内保留少量随机变化，不再额外添加竖向弹丸偏移。
- 腰射散布倍率 `0.75`。正常腰射误差仍会使整束弹丸偏移，鸭舌只改变弹丸之间的分布形状。
- 保留当前弹药的弹丸数量、总伤害、射程、弹速、后坐力和 ADS 耗时；不叠加普通收束器的弹丸散布减少 35%。横向展开沿用原弹丸散布半角，ADS 继续使用原有半角倍率。
- 独头弹保持单发直射，其腰射误差也按已确认的 0.75 倍率计算。
- 腰射准星以横向椭圆表示多弹丸的散布范围，独头弹保留等宽等高准星。
- 本地、客户端预测和服务端使用同一扇形函数；客户端预测与服务端保持相同随机种子及采样顺序。远端接收已计算的弹丸方向。
- 玩法判定读取已装备配方，不依赖装饰网格是否已经加载。改造通过现有物品配方保存、恢复和联机路径生效。

## 模型与材质

原创游戏外观：短扁壳体从圆形后座连续过渡到宽口鸭舌前端，出口上下收窄，浅黑凹面表现口部。只制作游戏外观，无现实制造内部结构。

沿用已安装配件的 SUPER90 实际枪口接座，+X 向前、+Z 向上。低矮下缘避让加长弹仓，原厂与加长弹仓使用同一外观。枪口、瞄准导向及枪口效果位置随附件出口更新。

`ShotgunDuckbill01_Editable.blend` 保存可编辑模型；`Exports/` 包含 FBX、GLB 与三级 LOD 组。LOD0/1/2 为 7096 / 3064 / 1288 三角面。四区 WS1 材质采用平整法线、独立粗糙度及金属度，避免旧配件粗糙法线的表面问题。

制作脚本对齐圆角顶点在各截面的语义位置，去掉已具有几何倒角的渐扩壳体上的重复角度倒角，防止纵向四边形扭曲和锯齿反光。

## 图标与源文件

使用内置 imagegen 编辑模式，以实际模型参考 `References/shotgun_duckbill_actual_model.png` 和已认可金属框母版制作正式图标。

- 最终图标：`muzzle_shotgun_duckbill.png`。
- 提示词与参考路径：`generation_prompts.json`。
- 活动共享图标：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_duckbill.png`。
- UE 资产：`/Game/Weapons/CommonShotgun/Duckbill20261016`。
- `prepare_sources.py`、`author_model.py`、`package_runtime.py`、`render_icon_reference.py` 保存可重做的制作流程。
- `install_assets.py` 导入模型、材质与两个 Texture2D 图标，`integrate_catalog.py` 仅修改 SUPER90 的本配件选项。

实际导入与编译状态以 `install_receipt.json` 和 `build_*_receipt.json` 为准。没有启动游戏、自动测试或整枪验收渲染；实际装配、ADS 和弹道效果由用户在游戏中测试。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90Duckbill20261016`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
