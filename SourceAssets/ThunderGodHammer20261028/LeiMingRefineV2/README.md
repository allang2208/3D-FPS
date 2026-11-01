# 雷鸣符文现行制作入口

用户认可设计：`../LeiMingConceptV2/lei_ming_rune_design_v2.png`。

1. `author_relief.py` 从可编辑路径制作刻纹、物理高度、DirectX 法线和表面分区；不从概念图的灯光明暗反推法线。
2. `lei_ming_rune_refined.svg` 为同源路径的可编辑展开稿，PNG为工程导入输入。贴合使用相同的厘米/像素比例。
3. `lei_ming_rune_icon.png` 为内置 imagegen 生成的正式图标，提示词见 `icon_prompt.txt`。
4. `import_all.ps1` 走项目批次互斥；使用已有编辑器桥或后台 commandlet，仅保存本目录声明的资产。
5. `build_editor.ps1` 编译原生材质选择逻辑；只在无编辑器或 commandlet 占用时执行，已有 UBT 完成后才提交。

`import_receipt.json` 记录实际资产保存。`build-*-receipt.json` 记录实际原生构建。它们不表示实战或视觉验收。早期 ExclusiveRunesV1 的雷鸣源留作历史，重导雷鸣使用本入口；回响仍使用原入口。
