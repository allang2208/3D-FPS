"""Render the fountain in the running editor (non-PIE only) via SceneCapture2D and export a
PNG so the fix can be inspected before delivery. Recipe from SourceAssets/RomanColumn20260915/
preview_engine_20260917.py: spawn capture -> explicit capture_scene() x3 -> export_render_target."""

import unreal

OUT_DIR = "D:/FPS3D/FPSGAME/Saved/FountainShots"
FOUNTAIN = unreal.Vector(1350.0, -1550.0, 0.0)

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les is None:
    print("[shot] no LevelEditorSubsystem (editor still booting)")
    raise SystemExit(0)
import os
if os.environ.get("FOUNTAIN_HEADLESS") != "1":
    # is_in_play_in_editor() access-violates in commandlets; only ask inside the real editor
    if les.is_in_play_in_editor():
        print("[shot] PIE ACTIVE - editor screenshots come out black; run this after PIE stops")
        raise SystemExit(0)
else:
    print("[shot] headless commandlet - never PIE, skipping query")

sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = sub.get_editor_world()
wpath = world.get_path_name() if world else ""
print("[shot] world=%s" % wpath)
if "DayNight_Lighting" not in wpath:
    if not les.load_level("/Game/GameMaps/DayNight_Lighting"):
        print("[shot] level load failed")
        raise SystemExit(0)
    world = sub.get_editor_world()

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
fs = [a for a in actor_sub.get_all_level_actors() if a.get_actor_label() == "RomanFountain1"]
print("[shot] fountain actors=%d" % len(fs))
if len(fs) == 1:
    loc = fs[0].get_actor_location()
    print("[shot] fountain at (%.0f,%.0f,%.0f)" % (loc.x, loc.y, loc.z))

# two angles: the user's low close view of the bottom basin + a wider three-quarter
VIEWS = [
    ("low_close", unreal.Vector(2250.0, -900.0, 500.0), -9.0, -142.0),
    ("wide", unreal.Vector(2600.0, -2300.0, 900.0), -18.0, -38.0),
]
rt = unreal.RenderingLibrary.create_render_target_2d(world, 1440, 810, unreal.TextureRenderTargetFormat.RTF_RGBA8, True)
capture = actor_sub.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 5000), unreal.Rotator(0, 0, 0))
comp = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
comp.set_render_target(rt)
comp.capture_source = unreal.SceneCaptureSource.SCS_FINAL_TONECURVE_HDR  # tonemapped LDR-ish
comp.fov_angle = 55.0

for name, pos, pitch, yaw in VIEWS:
    capture.set_actor_location(pos, False, True)
    capture.set_actor_rotation(unreal.Rotator(0.0, pitch, yaw), False, True)
    for _ in range(3):
        comp.capture_scene()
    out = unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, "fountain_%s" % name)
    print("[shot] %s exported=%s -> %s/fountain_%s.png" % (name, out, OUT_DIR, name))

capture.destroy_actor()
print("[shot] DONE")
