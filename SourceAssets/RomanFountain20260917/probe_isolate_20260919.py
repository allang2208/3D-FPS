"""组件隔离拍：逐个隐藏喷泉的网格组件，确定"画面里每一块到底是谁渲染的"。
同时读回每个组件的逐槽材质名。全程不保存。"""

import math
import unreal

OUT_DIR = "D:/FPS3D/FPSGAME/Saved/FountainShots"
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("[iso] PIE ACTIVE")
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
sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 10.0)
tmp.append(sun)
tmp.append(actor_sub.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)))
skyl = actor_sub.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 2000))
try:
    skyl.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
except Exception:
    pass
tmp.append(skyl)

f = [a for a in actor_sub.get_all_level_actors() if a.get_actor_label() == "RomanFountain1"][0]
comps = {}
for c in f.get_components_by_class(unreal.StaticMeshComponent):
    comps[c.get_name()] = c
for name, c in sorted(comps.items()):
    mesh = c.get_editor_property("static_mesh")
    slots = []
    if mesh:
        for i in range(len(mesh.get_editor_property("static_materials") or [])):
            m = mesh.get_material(i)
            slots.append(m.get_name() if m else "None")
    # 组件级覆盖材质
    overrides = []
    for i in range(c.get_num_materials()):
        m = c.get_material(i)
        overrides.append(m.get_name() if m else "None")
    print("[iso] %s mesh=%s asset_slots=%s comp_overrides=%s vis=%s" % (
        name, mesh.get_name() if mesh else None, slots, overrides, c.is_visible()))


def look_at(eye, target):
    dx, dy, dz = target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]
    return unreal.Rotator(0.0, math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)))


EYE = (2350.0, -2150.0, 560.0)
TARGET = (1350.0, -1550.0, 300.0)
rt = unreal.RenderingLibrary.create_render_target2d(world, 1440, 810, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = actor_sub.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 9000), unreal.Rotator(0, 0, 0))
comp = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("fov_angle", 50.0)
tr = unreal.Transform()
tr.translation = unreal.Vector(*EYE)
tr.rotation = look_at(EYE, TARGET).quaternion()
cap.set_actor_transform(tr, False, True)


def shoot(tag):
    for _ in range(4):
        comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, tag)
    print("[iso] shot %s" % tag)


CASES = [
    ("iso_all", []),
    ("iso_nofx", ["FountainWaterFx"]),
    ("iso_main_only", ["FountainWaterFx", "FountainWater"]),
    ("iso_fx_water", ["FountainMesh"]),
    ("iso_water_only", ["FountainMesh", "FountainWaterFx"]),
]
for tag, hidden in CASES:
    for name, c in comps.items():
        c.set_visibility(name not in hidden, False)
    shoot(tag)
for name, c in comps.items():
    c.set_visibility(True, False)
cap.destroy_actor()
for a in tmp:
    a.destroy_actor()
print("[iso] DONE")
