"""Offline verification for the installed Hospital Bed:
1) hard-wiring read-back of every material property input;
2) best-effort SceneCapture render (skipped if no world in commandlet).
"""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
E = u.EditorAssetLibrary
MAT_DIR = "/Game/Props/HospitalBed20260929/Materials"
MESH = "/Game/Props/HospitalBed20260929/SM_HospitalBed"

report = {"materials": {}, "render": None}

for name in ["M_HospitalBed_Pillow", "M_HospitalBed_Linen", "M_HospitalBed_Frame"]:
    mat = E.load_asset(MAT_DIR + "/" + name)
    info = {"expressions": u.MaterialEditingLibrary.get_num_material_expressions(mat)}
    props = {
        "BaseColor": u.MaterialProperty.MP_BASE_COLOR,
        "Metallic": u.MaterialProperty.MP_METALLIC,
        "Roughness": u.MaterialProperty.MP_ROUGHNESS,
        "Normal": u.MaterialProperty.MP_NORMAL,
        "AO": u.MaterialProperty.MP_AMBIENT_OCCLUSION,
    }
    for label, prop in props.items():
        node = u.MaterialEditingLibrary.get_material_property_input_node(mat, prop)
        info[label] = type(node).__name__ if node else None
    samples = [type(n).__name__ for n in u.MaterialEditingLibrary.get_material_expressions(mat)
               if isinstance(n, u.MaterialExpressionTextureSample)]
    info["texture_samples"] = len(samples)
    sts = []
    for n in u.MaterialEditingLibrary.get_material_expressions(mat):
        if isinstance(n, u.MaterialExpressionTextureSample):
            try:
                sts.append(str(n.get_editor_property("sampler_type")))
            except Exception:
                sts.append("?")
    info["sampler_types"] = sts
    report["materials"][name] = info
print("MAT_REPORT", json.dumps(report["materials"]), flush=True)

# --- best-effort render ---
try:
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
except Exception as e:
    world = None
    print("NO_WORLD", e, flush=True)

if world:
    try:
        loc = u.Vector(0, 0, 100)
        rot = u.Rotator(0, 0, 0)
        bed = u.EditorAssetLibrary.load_asset(MESH)
        actor = u.EditorLevelLibrary.spawn_actor_from_class(u.StaticMeshActor, loc, rot)
        mc = actor.get_editor_property("static_mesh_component")
        mc.set_static_mesh(bed)
        mc.set_mobility(u.ComponentMobility.MOVABLE)
        sun = u.EditorLevelLibrary.spawn_actor_from_class(
            u.DirectionalLight, u.Vector(300, 300, 400), u.Rotator(-45, 30, 0))
        comp = sun.get_component_by_class(u.DirectionalLightComponent) if sun else None
        if comp:
            comp.set_mobility(u.ComponentMobility.MOVABLE)
            comp.set_intensity(15.0)
        sky = u.EditorLevelLibrary.spawn_actor_from_class(u.SkyLight, u.Vector(0, 0, 500))
        sc = sky.get_component_by_class(u.SkyLightComponent) if sky else None
        if sc:
            sc.set_mobility(u.ComponentMobility.MOVABLE)
            sc.set_editor_property("real_time_capture", True)
            sc.set_intensity(3.0)
        cam_loc = u.Vector(260, 260, 120)
        target = u.Vector(0, 0, 60)
        direction = (target - cam_loc)
        direction.normalize()
        rot2 = u.MathLibrary.find_look_at_rotation(cam_loc, target)
        rt = u.AssetToolsHelpers.get_asset_tools().create_asset(
            "RT_HospitalBedVerify", "/Game/Props/HospitalBed20260929",
            u.TextureRenderTarget2D, u.TextureRenderTargetFactoryNew())
        rt.set_editor_property("size_x", 1024)
        rt.set_editor_property("size_y", 768)
        rt.set_editor_property("render_target_format", u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cap = u.EditorLevelLibrary.spawn_actor_from_class(u.SceneCapture2D, cam_loc, rot2)
        c = cap.get_component_by_class(u.SceneCaptureComponent2D)
        c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_editor_property("texture_target", rt)
        c.set_editor_property("capture_source", u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("fov_angle", 45.0)
        c.capture_scene()
        import os
        out_dir = "D:/FPS3D/FPSGAME/SourceAssets/HospitalBed20260929/verify"
        os.makedirs(out_dir, exist_ok=True)
        u.RenderingLibrary.export_render_target(world, rt, out_dir, "bed_verify")
        for a in [actor, sun, sky, cap]:
            if a:
                a.destroy_actor()
        report["render"] = str(out_dir + "/bed_verify")
        u.EditorAssetLibrary.delete_asset("/Game/Props/HospitalBed20260929/RT_HospitalBedVerify")
        print("RENDER_SAVED", out_dir, flush=True)
    except Exception as e:
        report["render"] = "ERR " + str(e)
        print("RENDER_ERR", e, flush=True)

(O / "verify_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("VERIFY_DONE", flush=True)
