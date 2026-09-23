# PKM 弹药箱军绿色漆面恢复

2026-09-23。用户确认弹药箱原来为绿色，要求修复后续统一枪钢时被覆盖的问题。

## 原因

`Bipod07/surface_and_skin.py` 将 `PKM_AmmoBoxPaint` 和枪钢共同列入 Body 烘焙组。现用网格的 `PKM_QBZ_Body__OldBox`、`PKM_QBZ_Body__NewBox` 因此一直使用机匣的深灰 QBZ 枪钢，之后 Finish20 划痕/雨水和 HandleFinish27 哑光处理也沿用了该绑定。这与 SectionFix09 已修复的重导入槽名错乱是两处不同问题。

## 制作与接入

- 从现用枪钢的干/湿材质各复制一份弹箱专用材质到 `/Game/Weapons/PKMLowpoly20260922/AmmoBox30/Materials`。只在两份副本的基础漆层恢复 Refinement06 中的线性军绿色 `.047, .065, .025`；保留当前图集提供的有限明暗变化。
- 完整漆面金属度为 0，既有细微划痕遮罩提供少量露钢。保留 HandleFinish27 的哑光粗糙度、细涂层纹理及微划痕；原结构法线、AO、UV 采样和湿膜/雨滴节点不替换。
- 现用 `Accessories14/SK_PKM_Manny_Modular` 的槽 8（OldBox）与槽 11（NewBox）绑定同一新干燥材质；将其湿润对应材质加入现用 `Finish20/DA_PKM_WetMaterials`，保留原有其它映射。换弹新旧箱保持一致。
- `Belt08/material_binding.py` 为这两种弹箱分区优先解析本轮专用漆面，避免后续共用导入器按 `PKM_QBZ_Body` 前缀再次覆盖成枪钢。原有槽名/槽序继续服务换弹可见性逻辑。
- 本轮为材质修复，不重导几何或骨骼，不更改源 Blend、手臂 UV、动画、枪身和改造件材质。历史 Blend 的弹箱材料名仍含 QBZ；引擎导入绑定以弹箱独立覆盖规则为准。

## 文件

- `restore_box_paint.py`：制作、材质必要编译、正式绑定和保存入口。
- `OlivePaint.hlsl`、`PaintMetallic.hlsl`：弹箱漆层与露钢细纹。
- `BeforeImport/`：操作前正式网格与雨水表备份。
- `import_receipt.json`：保存资产、前后两槽绑定及湿材质映射。
- `import_background.log`、`import_console.log`：后台 Python commandlet 日志。

已后台执行并保存两份材质、正式枪械网格及雨水表，退出码 0。无需 C++ 构建。没有启动交互式编辑器、PIE、游戏测试或验收渲染，颜色和雨天表现由用户在游戏中确认。
