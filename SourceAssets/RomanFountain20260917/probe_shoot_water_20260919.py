"""只读+临时改参对照拍：定位"水面平板"的环节。

步骤：
1. 读 MIC_FountainWaveWater 覆盖值 + M_FountainWaveWater 的 WPO/Normal 接在哪个节点 + 组件属性；
2. 拍 wide（现状）；
3. 隐藏 WaterMesh 拍 wide_hidden（确认淡蓝盘是不是 WaterWaves 网格）；恢复；
4. WaveHeight=60 / NormalSlope=3 拍 jet_big（确认法线链是否活着）；恢复原值。
全程不保存任何资产/关卡。
"""

import math
import unreal

OUT_DIR = "D:/FPS3D/FPSGAME/Saved/FountainShots"
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("[probe] PIE ACTIVE")
    raise SystemExit(0)
sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = sub.get_editor_world()
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

mic = unreal.load_asset("/Game/Props/RomanFountain20260917/Materials/MIC_FountainWaveWater")
mat = unreal.load_asset("/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWater")
print("[probe] mic=%s mat=%s" % (bool(mic), bool(mat)))
if mic:
    for lst in ("scalar_parameter_values", "vector_parameter_values"):
        vals = mic.get_editor_property(lst) or []
        names = []
        for v in vals:
            try:
                names.append("%s=%s" % (v.parameter_info.name, getattr(v, "parameter_value", "?")))
            except Exception:
                names.append("?")
        print("[probe] %s: %s" % (lst, ", ".join(names)))
if mat:
    MEL = unreal.MaterialEditingLibrary
    for prop in ("MP_WORLD_POSITION_OFFSET", "MP_NORMAL", "MP_OPACITY", "MP_BASE_COLOR", "MP_EMISSIVE_COLOR"):
        node = MEL.get_material_property_input_node(mat, getattr(unreal.MaterialProperty, prop))
        print("[probe] %s <- %s" % (prop, node.get_class().get_name() if node else "NONE"))
    print("[probe] blend=%s tlm=%s tangent=%s two_sided=%s" % (
        mat.get_editor_property("blend_mode"), mat.get_editor_property("translucency_lighting_mode"),
        mat.get_editor_property("tangent_space_normal"), mat.get_editor_property("two_sided")))

f = [a for a in actor_sub.get_all_level_actors() if a.get_actor_label() == "RomanFountain1"][0]
comps = {c.get_name(): c for c in f.get_components_by_class(unreal.StaticMeshComponent)}
wm = comps.get("FountainWater")
wm_mesh = wm.get_editor_property("static_mesh") if wm else None
wpo_prop = "?"
if wm:
    for cand in ("b_evaluate_world_position_offset", "evaluate_world_position_offset",
                 "bEvaluateWorldPositionOffset"):
        try:
            wpo_prop = "%s=%s" % (cand, wm.get_editor_property(cand))
            break
        except Exception:
            continue
print("[probe] FountainWater comp=%s mesh=%s vis=%s wpo=%s" % (
    bool(wm), wm_mesh.get_name() if wm_mesh else None,
    wm.is_visible() if wm else None, wpo_prop))

# 临时日光（编辑器模式关卡没有太阳/天空；拍完销毁，不存关卡）
tmp = []
for a in list(actor_sub.get_all_level_actors()):
    if a.get_class().get_name() in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "SceneCapture2D"):
        a.destroy_actor()
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


def look_at(eye, target):
    dx, dy, dz = target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]
    return unreal.Rotator(0.0, math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)))


F = (1350.0, -1550.0)
VIEWS = [("wide", (2750.0, -2750.0, 760.0), (F[0], F[1], 320.0)),
         ("jet", (1850.0, -2050.0, 900.0), (F[0], F[1], 640.0))]
rt = unreal.RenderingLibrary.create_render_target2d(world, 1440, 810, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = actor_sub.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 9000), unreal.Rotator(0, 0, 0))
comp = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("fov_angle", 55.0)


def shoot(tag, view):
    eye, target = VIEWS[0][1], VIEWS[0][2]
    for n, e, t in VIEWS:
        if n == view:
            eye, target = e, t
    tr = unreal.Transform()
    tr.translation = unreal.Vector(*eye)
    tr.rotation = look_at(eye, target).quaternion()
    cap.set_actor_transform(tr, False, True)
    for _ in range(4):
        comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, tag)
    print("[probe] shot %s" % tag)


shoot("p_now_wide", "wide")
if wm:
    wm.set_visibility(False, False)
    shoot("p_hidden_wide", "wide")
    wm.set_visibility(True, False)
old = {}
if mic:
    for name, val, fallback in (("WaveHeight", 60.0, 22.0), ("NormalSlope", 3.0, 1.6)):
        try:
            old[name] = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mic, name)
        except Exception:
            old[name] = fallback
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mic, name, val)
    mic.update_material_instance() if hasattr(mic, "update_material_instance") else None
    shoot("p_big_jet", "jet")
    shoot("p_big_wide", "wide")
    for name, val in old.items():
        if val is not None:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mic, name, val)
cap.destroy_actor()
for a in tmp:
    a.destroy_actor()
print("[probe] DONE")
