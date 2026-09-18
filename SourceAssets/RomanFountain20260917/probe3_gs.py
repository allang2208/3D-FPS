"""Probe 3: GeometryScript scaling route + Fab water/sound inventory (single read-only dispatch)."""

import unreal

print("[p3] ModelingService present:", hasattr(unreal, "ModelingService"))
print("[p3] GS_Transforms scale-ish:", sorted([n for n in dir(unreal.GeometryScript_Transforms) if "scale" in n.lower()]))
print("[p3] DynamicMeshLib copy/overwrite:", sorted([n for n in dir(unreal.DynamicMeshLibrary) if "copy" in n.lower() or "overwrite" in n.lower()]))
print("[p3] GS_ScriptUtil:" if hasattr(unreal, "GeometryScript_ScriptUtil") else "[p3] no GS_ScriptUtil",
      sorted([n for n in dir(unreal.GeometryScript_ScriptUtil) if "error" in n.lower()]) if hasattr(unreal, "GeometryScript_ScriptUtil") else "")

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    print("[p3] world=%s PIE=%s" % (w.get_path_name(), les.is_in_play_in_editor()))
except Exception as exc:  # noqa: BLE001
    print("[p3] world probe failed: %s" % exc)

# ---------------------------------------------------------------- Fab inventory: niagara + sounds
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for cls, label in (("NiagaraSystem", "niagara"), ("SoundWave", "soundwave"), ("SoundCue", "soundcue")):
    try:
        assets = reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", cls)
                                         if cls != "NiagaraSystem" else
                                         unreal.TopLevelAssetPath("/Script/Niagara", cls), True)
        hits = []
        for a in assets:
            nm = str(a.package_name)
            low = nm.lower()
            if any(k in low for k in ("water", "waterfall", "river", "stream", "splash", "fountain", "creek", "brook", "wave", "ocean", "lake", "flow")):
                hits.append(nm)
        print("[p3] %s total-waterish=%d" % (label, len(hits)))
        for h in hits[:60]:
            print("    ", h)
    except Exception as exc:  # noqa: BLE001
        print("[p3] %s search failed: %s" % (label, exc))

# what folders do the Fab packs live in?
try:
    for root in ("/Game/WaterMaterials", "/Game/FabNatureExport", "/Game/Fab"):
        print("[p3] dir %s exists=%s" % (root, unreal.EditorAssetLibrary.does_directory_exist(root)))
except Exception as exc:  # noqa: BLE001
    print("[p3] dir probe failed: %s" % exc)

print("[p3] DONE")
