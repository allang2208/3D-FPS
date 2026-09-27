# 暗纹猎弓木纹表面

把运行弓体／箭杆从 Fab 近黑 Phong 换成按结构分色的工程内木纹：弓体胡桃（`T_RottenWoodSurface_00A`），弓臂枫木、镶条红木、箭杆白蜡（`T_WoodSurface_00A`）。说明见 [制作记录](../../../Docs/Weapons/dark-bow-wood-finish-20260925.md)。

`
powershell -NoProfile -File SourceAssets/DarkBow20260925/Scripts/run_headless.ps1
  -Script SourceAssets/DarkBow20260925/WoodFinish20260925/recolor_structure_woods.py
  -LogName wood_recolor.log
`

已有 FPSGAME 编辑器时不要另起 commandlet，改走 Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript。`install_bow_wood.py` 会转调上述脚本。已存在且带表达式的 V2 母材质跳过重建。未运行游戏。
