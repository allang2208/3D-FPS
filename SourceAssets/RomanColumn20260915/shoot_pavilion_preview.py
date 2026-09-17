"""Clean up the icon probes and render studio-lit previews of the pavilion piece.

Runs inside the running editor via Tools/AssetPipeline/ue_python_exec.py. Everything it spawns
is destroyed again and the level is never saved; the probe pieces from the earlier run are
removed first so nothing is left in the user's level.

Two shots:
  icon-style  256x256, the panel's own framing (largest bbox edge = 78% of frame, -18/-35 view)
  hero        768x768, a closer 3/4 view for documentation
"""

import os
import time

import unreal

OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
FULL = "/Game/Props/RomanColumn20260915/SM_RomanPavilionFull_20"
COLUMN = "/Game/Props/RomanColumn20260915/SM_RomanColumn_Round_20"
Z = 200000.0                      # high above the level: only the piece and my lights are there
VIEW = unreal.Rotator(0.0, -18.0, -35.0)      # Python ctor is (roll, pitch, yaw)


def log(m):
    print("[shot] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# --- tidy up anything a previous probe left behind
gone = 0
for a in list(sub.get_all_level_actors()):
    if a.get_actor_label().startswith(("IconProbe_", "ShotRig_", "IconLight_")):
        sub.destroy_actor(a)
        gone += 1
log("removed %d probe actors from earlier runs" % gone)


def spawn_static(path, x, y, label):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, Z),
                                   unreal.Rotator(0.0, 0.0, 0.0))
    a.set_actor_label(label)
    comp = a.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def spawn_light(cls, loc, rot, label, **props):
    light = sub.spawn_actor_from_class(cls, loc, rot)
    if not light:
        return None
    light.set_actor_label(label)
    comp = light.get_component_by_class(unreal.DirectionalLightComponent) if cls == unreal.DirectionalLight \
        else light.get_component_by_class(unreal.SkyLightComponent)
    if comp:
        for key, value in props.items():
            try:
                comp.set_editor_property(key, value)
            except Exception as exc:
                log("  light prop %s failed: %s" % (key, type(exc).__name__))
    return light


# a simple three-point studio: key + fill + ambient sky, all local to the probe spot
key = spawn_light(unreal.DirectionalLight, unreal.Vector(0.0, 0.0, Z + 2000.0),
                  unreal.Rotator(0.0, -50.0, -35.0), "IconLight_Key", intensity=6.0,
                  light_color=unreal.LinearColor(1.0, 0.97, 0.92))
fill = spawn_light(unreal.DirectionalLight, unreal.Vector(0.0, 0.0, Z + 1500.0),
                   unreal.Rotator(0.0, -10.0, 140.0), "IconLight_Fill", intensity=2.5,
                   light_color=unreal.LinearColor(0.82, 0.9, 1.0))
sky = spawn_light(unreal.SkyLight, unreal.Vector(0.0, 0.0, Z + 800.0), unreal.Rotator(0.0, 0.0, 0.0),
                  "IconLight_Sky", intensity=1.0)
log("lights: key=%s fill=%s sky=%s" % (key is not None, fill is not None, sky is not None))

pavilion = spawn_static(FULL, 0.0, 0.0, "IconProbe_Pavilion")
column = spawn_static(COLUMN, 6000.0, 0.0, "IconProbe_Column")


def shoot(actor, tag, size, view, fill_fraction, extra_distance=0.0, target_shift=0.0):
    comp = actor.static_mesh_component
    bb = comp.static_mesh.get_bounds()
    centre = actor.get_actor_location() + bb.origin + unreal.Vector(0.0, 0.0, target_shift)
    max_dim = max(bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2)
    ortho = max(24.0, max_dim / fill_fraction)
    distance = 300.0 + max_dim * 2.0 + extra_distance
    forward = view.get_forward_vector()
    loc = centre - forward * distance
    rt = unreal.RenderingLibrary.create_render_target2d(
        world, size, size, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB,
        unreal.LinearColor(0, 0, 0, 1), False)
    cap = sub.spawn_actor_from_class(unreal.SceneCapture2D, loc, view)
    c = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
    c.texture_target = rt
    c.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    c.projection_type = unreal.CameraProjectionMode.ORTHOGRAPHIC
    c.ortho_width = ortho
    for flag in ("atmosphere", "fog", "volumetric_fog", "motion_blur", "bloom"):
        try:
            getattr(c.show_flags, "set_%s" % flag)(False)
        except Exception:
            pass
    for _ in range(3):
        c.capture_scene()
        time.sleep(0.6)
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, tag)
    path = os.path.join(OUT, tag)
    ok = os.path.exists(path) and os.path.getsize(path) > 10000
    log("%-26s %s (%d B)  ortho=%.0f  cam=(%.0f,%.0f,%.0f)" % (
        tag, ok, os.path.getsize(path) if os.path.exists(path) else 0, ortho, loc.x, loc.y, loc.z))
    cap.destroy_actor()
    unreal.RenderingLibrary.release_render_target2d(rt)
    return ok


a = shoot(pavilion, "pavilion_card_256.png", 256, VIEW, 0.78)
b = shoot(pavilion, "pavilion_hero_768.png", 768, unreal.Rotator(0.0, -14.0, -40.0), 0.86)
c2 = shoot(column, "column_card_256.png", 256, VIEW, 0.78)

# leave nothing behind
for a_ in list(sub.get_all_level_actors()):
    if a_.get_actor_label().startswith(("IconProbe_", "IconLight_")):
        sub.destroy_actor(a_)
log("probe actors cleaned up; level not saved")
log("RESULT: " + ("PASS" if a and b and c2 else "CHECK"))
