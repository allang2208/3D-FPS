# 暗纹猎弓弓体结构重构

在原拆分笼子上加抄把、箭台、镶条、层板和弦槽，不再把 71k 细节弓当底模。说明见 Docs/Weapons/dark-bow-riser-form-20260925.md。

Blender：E:/Program Files/Blender Foundation/Blender 5.1/blender.exe --background --factory-startup --python-exit-code 1 --python SourceAssets/DarkBow20260925/RiserForm20260925/author_riser_form.py

已有 FPSGAME 编辑器时导入走 Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript SourceAssets/DarkBow20260925/RiserForm20260925/import_riser_form.py

不要另起 commandlet 覆盖同一工程。未运行游戏。
