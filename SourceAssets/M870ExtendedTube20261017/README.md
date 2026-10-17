# M870 弹仓延长管

专用弹仓改造 `m870_tube_extension`，容量增加 3 发（7 → 10），仅增加容量。

- `author_tube.py`：原厂端盖、连续管体和接合套环的 Blender 制作；导出三 LOD FBX。
- `M870_ExtendedTube.blend`：可编辑模型，使用 M870 原生组件绑定坐标。
- `import_assets.py`：后台实际导入、材质适配、原生前端盖 24 面材质分组及保存。
- `integrate_catalog.py`：精确合并 M870 改造项，并修正此前腰射扩散误改的两项。
- `finish.ps1`：共用 UE 资产批次互斥，导入后完成 Editor 正常构建；不启动 GUI 或游戏。
- `authoring_receipt.json`、`catalog_receipt.json`、`import_receipt.json`：制作、目录及实际保存记录。

原厂端盖与贴图来源沿用 M870 Tactical（WillisChiejina，CC BY 4.0）：https://sketchfab.com/3d-models/m870-tactical-fad4289d1083447d9c8cc833362b04c6 。延长管新管体为本项目程序建模，原端盖前移且边缘细分；来源许可记录保留于 `SourceAssets/M870Tactical20261015/acquisition_receipt.json`。图标引用项目已采用的 SUPER90 共享延长管图，不复制或重新生成。

没有修改手臂姿态、动画或抓握接触。未运行游戏验收。详细接入说明：`Docs/Weapons/m870-extended-tube-20261017.md`。
