# Receiver finish authoring

This folder contains original authoring scripts for the M4/AKM attachment finish pass. It does not redistribute the source meshes, receiver textures, material graphs, or reference animation samples. Restore the licensed local project content first; see [AssetSetup](../../Docs/AssetSetup.md).

The default host is `D:/FPS3D/FPSGAME`, Blender 5.1 and Unreal 5.8. Python entry points execute when run; review their output paths before invoking them. The workflow writes weapon-private variants and preserves original source assets.

1. `export_parts.py` runs inside Unreal Python: exports current attachment meshes into `Sources`, records material bindings in `sources.json`, and backs up the source assets. `read_m4_graph.py` is an optional diagnostic for the receiver's effective conversion graph.
2. `prepare_profiles.py` runs in Python with Pillow: crops the approved M4 receiver region and writes `profiles.json`. AKM uses the existing licensed SovietFab ArmSupport material tiles. The M4 shininess/sRGB conversion intentionally follows the current receiver.
3. `author_uv.py` runs in Blender: loads the exported meshes, appends coating UVs, preserves original channels and writes the 14 FBXs, authoring record and editable Blend.
4. `import_finish.py` runs inside Unreal Python: creates private per-rifle materials/meshes under `/Game/Weapons/AttachmentFinish20260913` and writes `installed.json`. Runtime paths and cook directories are included in the source change.

`inspect_materials.py` and `check_saved_assets.py` are read-only asset-check entry points, used only when the user requests checks. Their historical results are described in [the dated finish record](../../Docs/Weapons/attachment-receiver-finish-20260913.md); publishing these tools does not mean checks or game tests were rerun.

The local `Before`, `Sources`, `FBX`, `Textures`, Blend files and detailed asset receipts remain available on the original host. Retired failed attempts are in `trash/weapon-finish-publication-20260913` with a SHA-256 manifest. Do not replace current production inputs with those retired attempts.
