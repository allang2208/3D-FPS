"""Reproduce the panel's icon capture for the pavilion, with RHI (no -NullRHI).

The drawer thumbnail for a prefab is drawn by UVoxelBuildIcons: an orthographic capture whose
largest bounding-box edge fills IconFillFraction (0.78) of the frame, colour pass =
SCS_FinalToneCurveHDR, alpha pass = SCS_SceneColorHDR (unlit), the pair composited by
M_WeaponPreviewResolved. The pavilion is the first piece big enough (960 cm) that this could
break, and the game only logs a failure when Build() returns false - a blank capture looks
exactly like "the card has no picture".

This runs the same numbers and exports both passes, so blank vs fine is visible directly.

Run:  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -nosplash
      (deliberately WITHOUT -NullRHI; add -RenderOffscreen)
"""

import os
import time

import unreal

OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
FULL = "/Game/Props/RomanColumn20260915/SM_RomanPavilionFull_20"
SEGMENT = "/Game/Props/RomanColumn20260915/SM_BalustradeSegment_20"   # a known-good small piece
# Python Rotator ctor is (roll, pitch, yaw); the C++ source means pitch -18, yaw -35
ICON_VIEW = unreal.Rotator(0.0, -18.0, -35.0)
FILL = 0.78


def log(m):
    print("[icon] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log("rhi=%s world=%s" % (unreal.SystemLibrary.get_console_variable_string_value("r.RHI.Name"), world.get_name()))


def spawn_piece(path, x, y, label):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, 0.0),
                                   unreal.Rotator(0.0, 0.0, 0.0))
    if not a:
        log("spawn failed %s" % label)
        return None
    a.set_actor_label(label)
    comp = a.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def icon_capture(actor, tag, size=256):
    """Same numbers as UVoxelBuildIcons::Build for a prefab (Cells empty)."""
    comp = actor.static_mesh_component
    mesh = comp.static_mesh
    bb = mesh.get_bounds()
    centre = actor.get_actor_location() + bb.origin
    max_dim = max(bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2)
    ortho = max(24.0, max_dim / FILL)
    distance = 300.0 + max_dim * 2.0
    forward = ICON_VIEW.get_forward_vector()
    cam = centre - forward * distance
    log("%-10s bounds centre=(%.0f,%.0f,%.0f) maxdim=%.0f ortho=%.0f cam=(%.0f,%.0f,%.0f)" % (
        tag, centre.x, centre.y, centre.z, max_dim, ortho, cam.x, cam.y, cam.z))

    results = {}
    for name, source in (("color", unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR),
                         ("coverage", unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)):
        rt = unreal.RenderingLibrary.create_render_target2d(
            world, size, size, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB,
            unreal.LinearColor(0, 0, 0, 1), False)
        cap = sub.spawn_actor_from_class(unreal.SceneCapture2D, cam, ICON_VIEW)
        if not cap:
            log("capture actor failed")
            continue
        c = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
        c.texture_target = rt
        c.capture_source = source
        c.projection_type = unreal.CameraProjectionMode.ORTHOGRAPHIC
        c.ortho_width = ortho
        for flag in ("atmosphere", "fog", "volumetric_fog", "motion_blur", "bloom", "temporal_aa"):
            try:
                getattr(c.show_flags, "set_%s" % flag)(False)
            except Exception:
                pass
        try:
            c.show_flags.set_anti_aliasing(True)
            c.show_flags.set_lighting(name == "color")
            c.show_flags.set_dynamic_shadows(name == "color")
        except Exception:
            pass
        for _ in range(3):
            c.capture_scene()
            time.sleep(0.5)
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, "%s_%s.png" % (tag, name))
        path = os.path.join(OUT, "%s_%s.png" % (tag, name))
        size_b = os.path.getsize(path) if os.path.exists(path) else 0
        results[name] = size_b
        log("  %-9s -> %s (%d B)" % (name, os.path.exists(path), size_b))
        cap.destroy_actor()
        unreal.RenderingLibrary.release_render_target2d(rt)
    return results


# high above the level so the capture sees only the piece (show_only_actors is not
# settable from Python: "cannot be edited on templates")
Z = 200000.0
big = spawn_piece(FULL, 0.0, 0.0, "IconProbe_Pavilion") if False else None
big = None
for a in list(sub.get_all_level_actors()):
    if a.get_actor_label().startswith("IconProbe_"):
        sub.destroy_actor(a)
big = spawn_piece(FULL, 0.0, 0.0, "IconProbe_Pavilion")
small = spawn_piece(SEGMENT, 4000.0, 0.0, "IconProbe_Segment")
if big:
    big.set_actor_location(unreal.Vector(0.0, 0.0, Z), False, False)
if small:
    small.set_actor_location(unreal.Vector(4000.0, 0.0, Z), False, False)
log("=== pavilion at the icon's framing ===")
icon_capture(big, "pavilion_icon")
log("=== known-good small piece for comparison ===")
icon_capture(small, "segment_icon")
log("RESULT: DONE")
