# 鸭舌收束器：封闭侧壁修订

用户要求在 V2 基础上封闭左右两侧。保留上下鸭舌、顶部几何浅槽、肩部、刻槽安装环及紧固件，只新增两块有厚度的侧壁，保留前方横向开口。

侧壁沿现有唇板截面向前展开，顶底边埋入唇板接合区，后端与原肩部搭接；前端形成窄的竖向边框。外侧使用原主体材质，内侧使用原暗凹面材质，前缘沿用加工金属分区。新侧壁独立展开 UV、处理倒角与法线，旧部件几何、UV 和自定义法线保留。

- 可编辑源：`ShotgunDuckbill_ClosedSides_Editable.blend`。
- 作者脚本：`author_closed_sides.py`，从 V2 可编辑源/各级导出继续制作。
- 三级 LOD：10252 / 5320 / 2244 三角面，各级均包含封闭侧壁。
- 当前运行资源仍为 `/Game/Weapons/CommonShotgun/DuckbillV2_20261016/Meshes/SM_ShotgunDuckbillV2`，挂点、坐标、出口位置及配件 ID 均未改变。
- 现有五组材质直接复用，不重写其参数。修改前模型和图标备份在 `Before/`。
- 玩法保持横向散布和腰射散布倍率 0.75；独头弹规则、加长弹仓适配均沿用现有接入。
- 正式图标 `muzzle_shotgun_duckbill.png` 使用内置 imagegen 编辑模式，以更新后的实际模型参考修改原框图。提示词与输入记录见 `generation_prompts.json`。
- `References/shotgun_duckbill_actual_model.png` 是图标制作使用的 Blender 模型参考，不是 UE 运行截图。

通过现有资产路径重新导入模型与图标，并更新外观描述。C++ 源码和接口未变，不需要重新构建游戏二进制；静态网格生成与实际保存记录见 `install_receipt.json`。

未主动打开交互 UE、启动试玩或运行验收，实际效果交由用户测试。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90DuckbillClosedSides20261016`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
