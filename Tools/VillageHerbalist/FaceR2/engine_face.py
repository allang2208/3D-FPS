"""Read saved herbalist packages and render a fixed-distance portrait in an isolated host."""
import json
import os
from pathlib import Path

import unreal as ue


ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "Saved/HerbalistFaceReview"
STAGE = os.environ["HERBALIST_FACE_STAGE"]
SOURCE = "/Game/Characters/VillageHerbalist"
SETTINGS = ("srgb", "compression_settings", "lod_group", "lod_bias", "max_texture_size",
            "mip_gen_settings", "filter", "never_stream", "virtual_texture_streaming",
            "flip_green_channel", "compression_no_alpha", "address_x", "address_y")


def export(asset, path, exporter, options=None):
    task = ue.AssetExportTask()
    task.object = asset
    task.filename = str(path)
    task.exporter = exporter
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if options:
        task.options = options
    if not ue.Exporter.run_asset_export_task(task):
        raise RuntimeError("Could not export " + asset.get_path_name())


def json_property(obj, name):
    value = obj.get_editor_property(name)
    return value if isinstance(value, (str, bool, int, float)) else str(value)


mesh = ue.load_asset(SOURCE + "/SK_VillageHerbalist")
if not mesh:
    raise RuntimeError("The runtime mesh was missing.")
mesh_subsystem = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)
report = {"engine": ue.SystemLibrary.get_engine_version(), "mesh": mesh.get_path_name(),
          "lod_count": mesh_subsystem.get_lod_count(mesh), "slots": [], "textures": {},
          "geometry_pose": "imported reference pose", "capture_mesh_lod": 0}
for slot in mesh.materials:
    mat = slot.material_interface
    base = mat.get_base_material()
    textures = ue.MaterialEditingLibrary.get_used_textures(base)
    bound = []
    for tex in textures:
        if not isinstance(tex, ue.Texture2D):
            continue
        name = tex.get_name()
        bound.append(tex.get_path_name())
        report["textures"][name] = {
            "path": tex.get_path_name(), "size": [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()],
            "settings": {key: json_property(tex, key) for key in SETTINGS},
        }
        if STAGE == "before":
            export(tex, REVIEW / (name + ".png"), ue.TextureExporterPNG())
    report["slots"].append({"slot": str(slot.material_slot_name), "material": mat.get_path_name(),
                            "base_material": base.get_path_name(), "textures": bound})
if STAGE == "before":
    opts = ue.FbxExportOption()
    opts.level_of_detail = False
    opts.export_morph_targets = False
    export(mesh, REVIEW / "SK_VillageHerbalist.fbx", ue.SkeletalMeshExporterFBX(), opts)
(REVIEW / ("bindings-" + STAGE + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")

# new_blank_map is only safe on the disposable host created by engine_face.ps1.
if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() != (REVIEW / "Studio").resolve():
    raise RuntimeError("Portrait lighting requires the isolated studio host.")
world = ue.EditorLoadingAndSavingUtils.new_blank_map(False)
actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)


def spawn(kind, position=(0, 0, 0), rotation=None):
    return actors.spawn_actor_from_class(kind, ue.Vector(*position), rotation or ue.Rotator(), True)


body = spawn(ue.SkeletalMeshActor).skeletal_mesh_component
body.set_mobility(ue.ComponentMobility.MOVABLE)
body.set_skeletal_mesh_asset(mesh)
body.set_forced_lod(1)
for pitch, yaw, intensity in [(-32, -116, 4.0), (-15, -42, 1.3), (-36, 90, 2.0)]:
    light = spawn(ue.DirectionalLight, (0, 0, 300), ue.Rotator(pitch=pitch, yaw=yaw)).light_component
    light.set_mobility(ue.ComponentMobility.MOVABLE)
    light.set_intensity(intensity)
    light.set_cast_shadows(intensity > 3)
sky = spawn(ue.SkyLight).light_component
sky.set_mobility(ue.ComponentMobility.MOVABLE)
sky.set_editor_property("source_type", ue.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_editor_property("cubemap", ue.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
sky.set_intensity(0.6)
eye, target = ue.Vector(0, 108, 154), ue.Vector(0, 0, 153)
camera = spawn(ue.SceneCapture2D, eye.to_tuple(), ue.MathLibrary.find_look_at_rotation(eye, target))
capture = camera.capture_component2d
capture.capture_every_frame = False
capture.capture_on_movement = False
capture.capture_source = ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR
capture.fov_angle = 17.0
post = capture.get_editor_property("post_process_settings")
for field, value in {
    "auto_exposure_method": ue.AutoExposureMethod.AEM_MANUAL,
    "auto_exposure_apply_physical_camera_exposure": False, "auto_exposure_bias": 0.38,
    "vignette_intensity": 0.0, "bloom_intensity": 0.0, "motion_blur_amount": 0.0,
}.items():
    post.set_editor_property("override_" + field, True)
    post.set_editor_property(field, value)
capture.set_editor_property("post_process_settings", post)
for command in ("r.ScreenPercentage 100", "r.TextureStreaming 0", "r.Shadow.Virtual.Enable 0"):
    ue.SystemLibrary.execute_console_command(world, command)
ue.AutomationLibrary.finish_loading_before_screenshot()
rt = ue.RenderingLibrary.create_render_target2d(world, 1024, 1024, ue.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
capture.texture_target = rt
for _ in range(4):
    capture.capture_scene()
image = "ue-" + STAGE + ".png"
ue.RenderingLibrary.export_render_target(world, rt, str(REVIEW), image)
report["camera"] = {"eye_cm": eye.to_tuple(), "target_cm": target.to_tuple(), "fov": capture.fov_angle,
                    "pixels": [1024, 1024], "texture_streaming": False, "exposure_bias": 0.38}
(REVIEW / ("bindings-" + STAGE + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
