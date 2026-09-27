# Bow Modular V13

Full integration record: [dark-bow-modular-v13-20260926.md](../../Docs/Weapons/dark-bow-modular-v13-20260926.md).

Production order: Blender `author_parts.py` → `run_import.ps1` (asset save then catalog activation) → Blender `render_icons.py` → Python `install_icons.py` → `run_icon_import.ps1` (Texture2D save). Render scripts produce catalog artwork, not gameplay acceptance captures. The editor is never launched interactively by these scripts; an already-open editor uses the existing batch mutex bridge.

Retained mesh source: `../DarkBow20260925/WoodLongbow20260925/WoodLongbow_Editable.blend`. Retained sight source: `../BowWoodSight20260926/Bow_CarvedWoodSight.blend`. Modular source and FBXs use centimetres; icon copies explicitly convert centimetres to metres, including the small support meshes. Wood textures remain the retained 4K base/ORM/normal set. Central wrap surface geometry and UVs are unchanged.

`authoring.json`, asset receipts and icon receipts describe the created/saved artifacts. Strong-draw body tuning intentionally shares the factory mesh/icon. Arrow mesh is independent of the new arrow support. All source files stay local. No game test or visual acceptance was performed.
