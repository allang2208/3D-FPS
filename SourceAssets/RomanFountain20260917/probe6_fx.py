"""Probe 6: exhaustive audio listing of the Fab/audio folders + FountainLightweight usability."""

import unreal

# every sound in the plausible folders, no keyword filter
for root in ("/Game/FabNatureExport", "/Game/WaterMaterials", "/Game/Audio", "/Game/Weather"):
    for cls in ("SoundWave", "SoundCue", "SoundBase", "MetaSoundSource"):
        try:
            assets = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
        except Exception:
            break
        break
    exists = unreal.EditorAssetLibrary.does_directory_exist(root)
    print("[p6] folder %s exists=%s" % (root, exists))
    if exists:
        found = []
        for a in unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
            if any(str(a).endswith(t) for t in (".SoundWave", ".SoundCue", ".MetaSoundSource")):
                found.append(str(a))
        print("[p6]   sounds=%d" % len(found))
        for f in found[:80]:
            print("     ", f)

# FountainLightweight: loadable? bounds? user params?
for path in ("/Niagara/DefaultAssets/Templates/Systems/FountainLightweight",
             "/Game/_SplineVFX/NS/NS_Spline_WaterSplash",
             "/Game/Weather/VFX/NS_FPS_SurfaceSplashes"):
    a = unreal.load_asset(path)
    print("[p6] load %s -> %s" % (path, type(a).__name__ if a else None))
    if a and type(a).__name__ == "NiagaraSystem":
        bb = a.get_bounds() if hasattr(a, "get_bounds") else None
        print("      bounds=%s" % (bb,))

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    print("[p6] world=%s PIE=%s" % (w.get_path_name(), les.is_in_play_in_editor()))
except Exception as exc:  # noqa: BLE001
    print("[p6] world probe failed: %s" % exc)
print("[p6] DONE")
