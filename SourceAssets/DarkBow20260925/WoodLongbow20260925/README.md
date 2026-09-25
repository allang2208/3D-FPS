# 木质长弓替换

Sadra 免费木质长弓，拆烘焙弦后按厘米 FBX 导入。说明见 Docs/Weapons/dark-bow-wood-longbow-20260925.md。

Blender：E:/Program Files/Blender Foundation/Blender 5.1/blender.exe --background --factory-startup --python SourceAssets/DarkBow20260925/WoodLongbow20260925/author_wood_longbow.py

厘米导出：author_wood_longbow.py 量完后把顶点写成厘米再出 `Export/SM_DarkBow_WoodLongbow_cm.fbx`；已有 Blend 用 export_fbx_mesh.py。米制 FBX／GLB／40k 探针已归档 trash/wood-longbow-probes-20260926/。

已有 FPSGAME 编辑器时导入走 Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript SourceAssets/DarkBow20260925/WoodLongbow20260925/import_wood_longbow.py

不要另起 commandlet 覆盖同一工程。未运行游戏。