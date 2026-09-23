# SVD 后托拆分与连接杆改造

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

用户 2026-09-23 要求把现有 SVD 后托拆开，通过后托连接杆组装替换。此要求更新此前“保留原厂枪托”的范围；原厂后握把、弹匣与动作继续沿用。

## 结构

- 源模型使用已补全弹匣、修复 PSO 接缝的 `SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend`。导入时从当前运行视模逐槽继承材质，保留后续 PSO 哑光升级。
- 在枪根局部坐标以 `y + 0.35*z = 0.112 m` 分离一体后托的肩托部分。保留右手握持轮廓；实际切口环补面，前段使用独立聚合物端面材质。
- 原厂肩托、贴腮板、尾垫及随托零件归入 `SVD_FactoryStock`，可整组隐藏和恢复。其余机匣、机械件、手模、UV 与材质身份保留。
- 新组件包括封闭机匣后座、上部连接榫、下支撑、单根连接杆、锁紧环、后套环及横向固定件。连接杆外径 23.2 mm、长 61 mm，插入替换枪托的现有接口。各套模型保持供体物理尺寸。
- 连接杆与枪托在作者 Blend 中是独立对象；运行时作为一个枪托组合切换，避免连接杆残留或与原厂肩托重叠。无需新增存档槽位。

## 替换选项与数据

SVD 新增 `stock` 槽：`false`、`skeleton`、`core_stock`、`qr_performance`、`tactical_telescopic`。后四种使用专用连接杆组合，`false` 恢复原厂肩托。

数值沿用既有通用枪托目录，连接杆不另加数值。使用现有 `SetGunsmithStock` 装配入口，因此角色、枪匠草稿/应用、独立展览、掉落模型及实例存档沿用同一选项。UI 制作五张单件选项图标及一张分类图标，属于生产资源，未进行验收渲染。

## 材质与来源

四种供体及实际源文件记录在 `geometry_inputs.json`、`authoring.json`，来自项目已经接入的 AKM 通用后托资产。仅复用现有本地资产，不改变其来源与公开分发许可。

新增连接座/杆沿用 SVD 当前哑光接口钢。替换后托金属区域使用本枪涂层、5 cm 物理 UV2 和 `SVDMatteDetail20260923` 细表面程序；原 UV0 结构法线、AO、聚合物和橡胶分区保留。干/湿材质映射合并到现有 SVD 天气材质表。

## 交付入口

- `SVD_StockModular_Editable.blend`：拆分后的完整可编辑视模。
- `SM_SVD_*.blend`、`Exports/`：四种独立组合及拆出的原厂肩托 FBX。
- `author_geometry.py` / `import_assets.py`：制作及后台导入保存。
- `author_icons.py` / `Icons/`：实际模型制作的选项图标。
- `update_catalog.py`：仅更新 SVD 目录条目，既有配件数值不变。
- `import_receipt.json`：网格、材质、图标及天气表的实际保存回执。
- 运行视模：`/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock`。
- 运行后托：该目录的 `Meshes/SM_SVD_{选项ID}`。

旧运行网格继续保留；本次不重导动画，不覆盖已经保存的抓握修订。按用户规则未启动 GUI 编辑器、PIE、游戏测试或验收预览。

## 落盘状态

- 后台 commandlet 已保存四套枪托组合、新的模块化视模、SVD 专用干/湿材质、天气映射及六张 UI 图标，回执状态为 `imported_and_saved`。
- `FPSGAMEEditor Win64 Development` 构建结果 `Succeeded`；本次 UBT 等待现有构建结束后报告目标已是最新，日志为 `build_editor.log`。
- 已修改运行网格路径、SVD 枪托装配分支、专用后托资产路径、SVD 目录条目及 Cook 目录。
- 未做游戏测试；原厂恢复、各后托组合的实际近景和枪匠操作效果交由用户测试。
