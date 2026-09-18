"""Probe 4: find the GeometryScript scale/copy/overwrite functions wherever they live."""

import unreal

gs_classes = [n for n in dir(unreal) if n.startswith("GeometryScript_")]
print("[p4] GeometryScript classes: %d" % len(gs_classes))
for cn in gs_classes:
    cls = getattr(unreal, cn)
    fns = [n for n in dir(cls) if any(k in n.lower() for k in ("scale", "copy_static", "overwrite_static"))]
    if fns:
        print("  %s: %s" % (cn, sorted(fns)))

# world / PIE state too
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    print("[p4] world=%s PIE=%s" % (w.get_path_name(), les.is_in_play_in_editor()))
except Exception as exc:  # noqa: BLE001
    print("[p4] world probe failed: %s" % exc)

print("[p4] DONE")
