"""Probe 5: exact signatures for the GS scale route + Fab water/niagara/sound inventory."""

import unreal

for fn in (unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh,
           unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh,
           unreal.GeometryScript_MeshTransforms.scale_mesh):
    print("[p5] --- %s%s" % (fn.__name__, getattr(fn, "__doc__", "")))

# ---------------------------------------------------------------- Fab inventory
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for cls_path, label in (("/Script/Niagara", "NiagaraSystem"), ("/Script/Engine", "SoundWave"),
                        ("/Script/Engine", "SoundCue")):
    try:
        assets = reg.get_assets_by_class(unreal.TopLevelAssetPath(cls_path, label), True)
        hits = []
        for a in assets:
            nm = str(a.package_name)
            low = nm.lower()
            if any(k in low for k in ("water", "waterfall", "river", "stream", "splash",
                                      "fountain", "creek", "brook", "ocean", "lake", "flow",
                                      "rain", "droplet", "drip")):
                hits.append(nm)
        print("[p5] %s water-ish=%d" % (label, len(hits)))
        for h in hits[:70]:
            print("     ", h)
    except Exception as exc:  # noqa: BLE001
        print("[p5] %s search failed: %s" % (label, exc))

for root in ("/Game/WaterMaterials", "/Game/FabNatureExport"):
    print("[p5] dir %s exists=%s" % (root, unreal.EditorAssetLibrary.does_directory_exist(root)))

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    print("[p5] world=%s PIE=%s" % (w.get_path_name(), les.is_in_play_in_editor()))
except Exception as exc:  # noqa: BLE001
    print("[p5] world probe failed: %s" % exc)
print("[p5] DONE")
