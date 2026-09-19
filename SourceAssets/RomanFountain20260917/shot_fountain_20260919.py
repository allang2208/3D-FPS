"""喷泉实拍（编辑器模式，非 PIE）：SceneCapture2D 三视角出图。

编辑器模式下关卡没有太阳/天空（昼夜是运行时 BP_FPS_DayNightManager 在 BeginPlay 生成的），
所以拍摄前临时 spawn 太阳 + SkyAtmosphere + SkyLight（real-time capture），拍完销毁、不存关卡。
相机朝向按 look-at 计算（yaw=atan2(dy,dx)，pitch=atan2(dz,水平距)）。
"""

import math
import unreal

OUT_DIR = "D:/FPS3D/FPSGAME/Saved/FountainShots"
TAG = "v21"

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("[shot] PIE ACTIVE - run after PIE stops")
    raise SystemExit(0)
sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = sub.get_editor_world()
if "DayNight_Lighting" not in world.get_path_name():
    if not les.load_level("/Game/GameMaps/DayNight_Lighting"):
        print("[shot] level load failed")
        raise SystemExit(0)
    world = sub.get_editor_world()
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# 上次失败运行可能留下临时灯：关卡本身没有太阳/天空/天光，见到就清掉
for a in list(actor_sub.get_all_level_actors()):
    if a.get_class().get_name() in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "SceneCapture2D"):
        print("[shot] removing leftover %s" % a.get_class().get_name())
        a.destroy_actor()

# ---- 临时日光三件套（只为本轮截图服务，拍完销毁） ----
tmp = []
sun = actor_sub.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000),
                                       unreal.Rotator(0.0, -52.0, 135.0))
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
sc.set_editor_property("intensity", 30.0)
sc.set_editor_property("light_color", unreal.Color(255, 245, 224, 255))
tmp.append(sun)
try:
    sky = actor_sub.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    tmp.append(sky)
except Exception as exc:
    print("[shot] no SkyAtmosphere: %s" % exc)
skyl = actor_sub.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 2000))
slc = skyl.get_component_by_class(unreal.SkyLightComponent)
try:
    slc.set_editor_property("real_time_capture", True)
except Exception as exc:
    print("[shot] skylight real_time_capture: %s" % exc)
tmp.append(skyl)
print("[shot] temp lighting spawned: %s" % [a.get_actor_label() for a in tmp])


def look_at(eye, target):
    dx, dy, dz = target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]
    horiz = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, horiz))
    return unreal.Rotator(0.0, pitch, yaw)


F = (1350.0, -1550.0)
VIEWS = [
    ("low_close", (2050.0, -1050.0, 190.0), (F[0], F[1], 170.0)),
    ("wide",      (2750.0, -2750.0, 760.0), (F[0], F[1], 320.0)),
    ("jet",       (1850.0, -2050.0, 900.0), (F[0], F[1], 640.0)),
]

rt = unreal.RenderingLibrary.create_render_target2d(world, 1440, 810, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
capture = actor_sub.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 9000), unreal.Rotator(0, 0, 0))
comp = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("fov_angle", 55.0)

for name, eye, target in VIEWS:
    tr = unreal.Transform()
    tr.translation = unreal.Vector(eye[0], eye[1], eye[2])
    tr.rotation = look_at(eye, target).quaternion()
    capture.set_actor_transform(tr, False, True)
    for _ in range(4):
        comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, "%s_%s" % (TAG, name))
    print("[shot] %s -> %s/%s_%s.png" % (name, OUT_DIR, TAG, name))

capture.destroy_actor()
for a in tmp:
    a.destroy_actor()
print("[shot] DONE (temp lighting destroyed, level NOT saved)")
