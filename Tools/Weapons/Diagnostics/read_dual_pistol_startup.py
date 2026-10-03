"""Read the existing PIE player's single/dual pose owners without changing play state."""
import json
from pathlib import Path
import unreal as u

def path(obj):
    return obj.get_path_name() if obj else None

def animation(anim):
    if not anim:
        return None
    return {"instance": path(anim), **{
        key: path(anim.get_editor_property(key))
        for key in ("idle_clip", "aim_clip", "action_clip", "grip_profile")
    }}

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report = {"world": path(world), "play_started_by_script": False}
pawn = u.GameplayStatics.get_player_character(world, 0) if world else None
if pawn:
    report["pawn"] = path(pawn)
    main = pawn.get_editor_property("akm_viewmodel")
    report["main"] = {"mesh": path(main.get_skeletal_mesh_asset()),
                      "animation": animation(main.get_anim_instance())}
    dual = pawn.get_editor_property("dual_pistols")
    report["hands"] = []
    for hand in dual.get_editor_property("hands"):
        mesh = hand.get_editor_property("mesh")
        cached = hand.get_editor_property("anim")
        clips = hand.get_editor_property("clips")
        item = hand.get_editor_property("item")
        report["hands"].append({
            "definition": item.get_editor_property("definition"),
            "mesh": path(mesh.get_skeletal_mesh_asset()) if mesh else None,
            "actual_animation": animation(mesh.get_anim_instance()) if mesh else None,
            "cached_animation": animation(cached),
            "cached_is_actual": bool(mesh and cached == mesh.get_anim_instance()),
            "dual_idle": path(clips.get("idle")),
        })
out = Path(u.Paths.project_saved_dir()) / "Diagnostics/DualPistolStartup20261003/runtime-before.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False), flush=True)
