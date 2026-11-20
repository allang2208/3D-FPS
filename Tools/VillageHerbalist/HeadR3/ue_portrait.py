"""Read published packages in an isolated studio and photograph both heads with matched lighting."""
import json
import math
import os
import shutil
from pathlib import Path

import unreal as ue


host = Path(os.environ["LINZHI_R3_HOST"]).resolve()
if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() != host:
    raise RuntimeError("Portrait creation requires the disposable studio")
out = Path(os.environ["LINZHI_R3_PORTRAITS"])
out.mkdir(parents=True, exist_ok=True)
softbox = os.environ.get("LINZHI_R3_SOFTBOX") == "1"
world = ue.EditorLoadingAndSavingUtils.new_blank_map(False)
actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)


def spawn(kind, position, rotation=None):
    return actors.spawn_actor_from_class(kind, ue.Vector(*position), rotation or ue.Rotator(), True)


body = spawn(ue.SkeletalMeshActor, (0, 0, 0)).skeletal_mesh_component
body.set_mobility(ue.ComponentMobility.MOVABLE)
body.set_forced_lod(1)
# Three large sources give a readable eye socket in both poses. The rear board
# gives the silhouette and fine hair a constant neutral studio background.
for pitch, yaw, intensity in [(-28, -116, 2.55), (-9, -48, 1.28), (-33, 92, 1.25)]:
    light = spawn(ue.DirectionalLight, (0, 0, 300), ue.Rotator(pitch=pitch, yaw=yaw)).light_component
    light.set_mobility(ue.ComponentMobility.MOVABLE)
    light.set_intensity(intensity)
    light.set_cast_shadows(False)
sky = spawn(ue.SkyLight, (0, 0, 0)).light_component
sky.set_mobility(ue.ComponentMobility.MOVABLE)
sky.set_editor_property("source_type", ue.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_editor_property("cubemap", ue.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
sky.set_intensity(1.05)
if softbox:
    for position, lumens, width, height in (
            ((46., 80., 185.), .36, 62., 52.),
            ((-51., 70., 161.), .16, 64., 65.),
            ((-10., -33., 190.), .08, 42., 62.)):
        aim = ue.MathLibrary.find_look_at_rotation(ue.Vector(*position), ue.Vector(0., 0., 153.))
        area = spawn(ue.RectLight, position, aim).rect_light_component
        area.set_mobility(ue.ComponentMobility.MOVABLE)
        area.set_editor_property("intensity_units", ue.LightUnits.LUMENS)
        area.set_intensity(lumens)
        area.set_source_width(width)
        area.set_source_height(height)
        area.set_attenuation_radius(350.)
        area.set_cast_shadows(False)
board_actor = spawn(ue.StaticMeshActor, (0, -90, 150))
board = board_actor.static_mesh_component
board.set_mobility(ue.ComponentMobility.MOVABLE)
board.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Cube"))
board_actor.set_actor_scale3d(ue.Vector(9, .05, 5))
back = board.create_dynamic_material_instance(0, ue.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
back.set_vector_parameter_value("Color", ue.LinearColor(.19, .176, .159, 1.))
camera = spawn(ue.SceneCapture2D, (0, 110, 154))
capture = camera.capture_component2d
capture.capture_every_frame = capture.capture_on_movement = False
capture.capture_source = (ue.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR if softbox
                          else ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
capture.fov_angle = 18.0
post = capture.get_editor_property("post_process_settings")
for field, value in {
    "auto_exposure_method": ue.AutoExposureMethod.AEM_MANUAL,
    "auto_exposure_apply_physical_camera_exposure": False, "auto_exposure_bias": .42,
    "vignette_intensity": 0., "bloom_intensity": 0., "motion_blur_amount": 0.,
}.items():
    post.set_editor_property("override_" + field, True)
    post.set_editor_property(field, value)
capture.set_editor_property("post_process_settings", post)
for command in ("r.ScreenPercentage 100", "r.TextureStreaming 0", "r.Shadow.Virtual.Enable 0"):
    ue.SystemLibrary.execute_console_command(world, command)
target_format = (ue.TextureRenderTargetFormat.RTF_RGBA16F if softbox
                 else ue.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
rt = ue.RenderingLibrary.create_render_target2d(world, 1280, 1280, target_format)
capture.texture_target = rt
root = "/Game/Characters/VillageHerbalist/"
report = {}
for revision, package in [("HeadR3", "HeadR3/SK_VillageHerbalist_HeadR3"), ("FaceR2", "SK_VillageHerbalist")]:
    if os.environ["LINZHI_R3_REVISION"] not in (revision, "studio"):
        continue
    mesh = ue.load_asset(root + package)
    if not mesh:
        raise RuntimeError("Missing published mesh: " + package)
    body.set_skeletal_mesh_asset(mesh)
    ue.AutomationLibrary.finish_loading_before_screenshot()
    entries = {}
    for view, yaw in [("front", 0.), ("three-quarter", 38.)]:
        angle = math.radians(yaw)
        target = ue.Vector(0., 0., 153.)
        eye = target + ue.Vector(108. * math.sin(angle), 108. * math.cos(angle), 1.)
        camera.set_actor_location_and_rotation(eye, ue.MathLibrary.find_look_at_rotation(eye, target), False, False)
        for _ in range(4):
            capture.capture_scene()
        name = revision + "-" + view + (".exr" if softbox else ".png")
        ue.RenderingLibrary.export_render_target(world, rt, str(host), name)
        rendered = host / name
        with rendered.open("rb") as stream:
            magic = b"\x76\x2f\x31\x01" if softbox else b"\x89PNG\r\n\x1a\n"
            if stream.read(len(magic)) != magic:
                raise RuntimeError("SceneCapture did not export the requested image: " + name)
        temporary = out / (name + "." + host.name + ".tmp")
        shutil.copyfile(rendered, temporary)
        os.replace(temporary, out / name)
        entries[name] = dict(eye=list(eye.to_tuple()), aim=list(target.to_tuple()), fov=capture.fov_angle)
    slots = {}
    for slot in mesh.materials:
        mat = slot.material_interface
        textures = ue.MaterialEditingLibrary.get_used_textures(mat.get_base_material())
        slots[str(slot.material_slot_name)] = dict(material=mat.get_path_name(),
            textures={t.get_path_name(): [t.blueprint_get_size_x(), t.blueprint_get_size_y()]
                      for t in textures if isinstance(t, ue.Texture2D)})
    report[revision] = dict(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(),
                            bones=body.get_num_bones(), slots=slots, views=entries)
    if revision == "HeadR3":
        albedo = ue.load_asset(root + "HeadR3/Textures/T_LinZhiHead_Color")
        asset_data = ue.AssetRegistryHelpers.create_asset_data(albedo)
        source_tag = asset_data.get_tag_value("AssetImportData")
        if source_tag:
            report[revision]["head_albedo_import"] = json.loads(source_tag)
(out / (os.environ["LINZHI_R3_REVISION"] + "-saved-package.json")).write_text(
    json.dumps(report, indent=2), encoding="utf-8")
