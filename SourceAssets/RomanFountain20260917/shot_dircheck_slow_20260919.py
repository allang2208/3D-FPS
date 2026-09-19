"""慢动作流向判别：FlowSpeed 临时 0.05（3 s 间隔位移约 27 cm ≈ 40 px，不混叠），
拍 dir_slow_a / dir_slow_b 后恢复 1.5。离线互相关定方向。"""

import math
import time
import unreal

OUT_DIR = "D:/FPS3D/FPSGAME/Saved/FountainShots"
MATDIR = "/Game/Props/RomanFountain20260917/Materials"
MEL = unreal.MaterialEditingLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("[dir] PIE ACTIVE")
    raise SystemExit(0)
sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = sub.get_editor_world()
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

for a in list(actor_sub.get_all_level_actors()):
    if a.get_class().get_name() in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "SceneCapture2D"):
        a.destroy_actor()
tmp = []
sun = actor_sub.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000),
                                       unreal.Rotator(0.0, -52.0, 135.0))
sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 30.0)
tmp.append(sun)
tmp.append(actor_sub.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)))
skyl = actor_sub.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 2000))
try:
    skyl.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
except Exception:
    pass
tmp.append(skyl)

mic = unreal.load_asset(MATDIR + "/MIC_FountainCascadeFlow")
MEL.set_material_instance_scalar_parameter_value(mic, "FlowSpeed", 0.05)


def look_at(eye, target):
    dx, dy, dz = target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]
    return unreal.Rotator(0.0, math.degrees(math.atan2(dz, math.hypot(dx, dy))),
                          math.degrees(math.atan2(dy, dx)))


EYE = (2050.0, -1850.0, 420.0)
TARGET = (1350.0, -1550.0, 380.0)
rt = unreal.RenderingLibrary.create_render_target2d(world, 1440, 810, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = actor_sub.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 9000), unreal.Rotator(0, 0, 0))
comp = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("fov_angle", 40.0)
tr = unreal.Transform()
tr.translation = unreal.Vector(*EYE)
tr.rotation = look_at(EYE, TARGET).quaternion()
cap.set_actor_transform(tr, False, True)

for tag in ("dir_slow_a", "dir_slow_b"):
    for _ in range(3):
        comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, tag)
    print("[dir] shot %s" % tag)
    if tag == "dir_slow_a":
        time.sleep(3.0)

MEL.set_material_instance_scalar_parameter_value(mic, "FlowSpeed", 1.5)
cap.destroy_actor()
for a in tmp:
    a.destroy_actor()
print("[dir] DONE (FlowSpeed restored 1.5)")
