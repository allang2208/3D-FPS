"""Capture real engine renders via SceneCapture2D + explicit capture_scene() + RT export.

Runs inside the running editor via Tools/AssetPipeline/ue_python_exec.py.
"""

import os
import time

import unreal

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"

BAL = "/Game/Props/RomanColumn20260915/SM_RomanBaluster_Small"
COL = "/Game/Props/RomanColumn20260915/SM_RomanColumn_Detailed"
SEG = "/Game/Props/RomanColumn20260915/SM_BalustradeSegment_20"


def log(m):
    print("[cap] " + m)


def spawn(path, x, y, label):
    m = unreal.EditorAssetLibrary.load_asset(path)
    a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, 0.0),
                                   unreal.Rotator(0.0, 0.0, 0.0))
    sm = a.get_component_by_class(unreal.StaticMeshComponent)
    sm.set_static_mesh(m)
    sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    a.set_actor_label(label)
    return a


for a in list(sub.get_all_level_actors()):
    if a.get_actor_label().startswith(("BalusterPreview", "ColumnPreview", "SegmentPreview", "ShotRig")):
        sub.destroy_actor(a)

spawn(BAL, 400.0, 300.0, "BalusterPreview_01")
spawn(COL, 700.0, 300.0, "ColumnPreview_01")
spawn(SEG, 1000.0, 300.0, "SegmentPreview_01")


def shoot(cam_pos, rot, fov, width, height, name):
    rt = unreal.RenderingLibrary.create_render_target2d(
        world, width, height, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB,
        unreal.LinearColor(0, 0, 0, 1), False)
    cap = sub.spawn_actor_from_class(unreal.SceneCapture2D, cam_pos, rot)
    c = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
    c.texture_target = rt
    c.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    c.fov_angle = fov
    for _ in range(3):
        c.capture_scene()
        time.sleep(0.8)
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, name)
    dst = os.path.join(OUT, name)
    ok = os.path.exists(dst) and os.path.getsize(dst) > 10000
    log("%s -> %s (%d B)" % (name, ok, os.path.getsize(dst) if os.path.exists(dst) else 0))
    cap.destroy_actor()
    unreal.RenderingLibrary.release_render_target2d(world, rt)
    return ok


wide = shoot(unreal.Vector(700.0, -1000.0, 420.0), unreal.Rotator(-14.0, 90.0, 0.0), 50.0, 1600, 900,
             "engine_preview_v2.png")
close = shoot(unreal.Vector(530.0, -430.0, 150.0), unreal.Rotator(-8.0, 90.0, 0.0), 35.0, 1600, 900,
              "engine_closeup_v2.png")
log("RESULT: " + ("PASS" if wide and close else "CHECK"))
