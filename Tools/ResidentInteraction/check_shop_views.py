"""Offscreen GPU regression for view-specific shop masks, depth occlusion and dark tones."""
import json
import os
from pathlib import Path

import unreal as u

out = Path(os.environ["SHOP_VIEW_AUDIT"]).resolve()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != out / "Host":
    raise RuntimeError("Run in the isolated lighting audit project.")
world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)


def spawn(cls, x, y):
    return actors.spawn_actor_from_class(cls, u.Vector(x, y, 0), u.Rotator(), True)


def surface(name, value):
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(
        name, "/Game/Audit", u.Material, u.MaterialFactoryNew())
    edit = u.MaterialEditingLibrary
    node = edit.create_material_expression(material, u.MaterialExpressionSubstrateUnlitBSDF)
    color = edit.create_material_expression(material, u.MaterialExpressionConstant3Vector)
    color.constant = u.LinearColor(value, value, value, 1)
    if not edit.connect_material_expressions(color, "", node, "EmissiveColor"):
        raise RuntimeError("Cannot connect calibration emissive")
    if not edit.connect_material_property(node, "", u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Cannot connect calibration surface")
    edit.recompile_material(material)
    return material


bright = surface("ShopCalibrationBright", 4.0)
dark = surface("ShopCalibrationDark", 0.14)
cube = u.load_asset("/Engine/BasicShapes/Cube")
for x, y, stencil, mat in [(200, -104, 176, bright), (200, -52, 191, bright),
                           (200, 0, 176, dark), (200, 52, 0, bright),
                           (200, 104, 176, bright), (150, 78, 0, bright)]:
    actor = spawn(u.StaticMeshActor, x, y)
    mesh = actor.static_mesh_component
    mesh.set_static_mesh(cube)
    actor.set_actor_scale3d(u.Vector(.10, .32, .58))
    mesh.set_material(0, mat)
    mesh.set_render_custom_depth(bool(stencil))
    mesh.set_custom_depth_stencil_value(stencil)

asset = u.load_asset("/Game/Characters/ResidentInteraction/M_ResidentShopHighlightResponse")
if not asset:
    raise RuntimeError("Missing production response material")
capture = spawn(u.SceneCapture2D, 0, 0).capture_component2d
capture.capture_every_frame = capture.capture_on_movement = False
capture.always_persist_rendering_state = True
capture.fov_angle = 90
capture.capture_source = u.SceneCaptureSource.SCS_FINAL_COLOR_HDR
target = u.RenderingLibrary.create_render_target2d(world, 480, 160, u.TextureRenderTargetFormat.RTF_RGBA16F)
capture.texture_target = target
pp = capture.post_process_settings
for prop, value in {"auto_exposure_method": u.AutoExposureMethod.AEM_MANUAL,
                    "auto_exposure_apply_physical_camera_exposure": False, "auto_exposure_bias": 0.,
                    "motion_blur_amount": 0., "vignette_intensity": 0., "bloom_intensity": 0.}.items():
    pp.set_editor_property("override_" + prop, True)
    pp.set_editor_property(prop, value)
capture.post_process_settings = pp
mid = u.MaterialLibrary.create_dynamic_material_instance(world, asset)
capture.add_or_update_blendable(mid, 1.0)
u.AutomationLibrary.finish_loading_before_screenshot()
values = {}
for mask in (0, 1, 32768, 32769):
    mid.set_scalar_parameter_value("VisibleResidentSlots", float(mask))
    for _ in range(3):
        capture.capture_scene()
    values[mask] = [round(u.RenderingLibrary.read_render_target_raw_pixel(
        world, target, px, 80, False).r, 5) for px in (112, 176, 240, 304, 368)]
base = values[0]
cases = {"bright_and_dark_inputs_detected": min(base[i] for i in (0, 1, 3, 4)) > base[2] + .1}
for mask in (1, 32768, 32769):
    row = values[mask]
    for i, name in enumerate(("first_resident", "last_resident", "dark", "environment", "occluder")):
        affected = (i == 0 and mask & 1) or (i == 1 and mask & 32768)
        cases[f"{mask}_{name}"] = (0 < row[i] < base[i] * .99 if affected else abs(row[i] - base[i]) < .005)
(out / "gpu-mask-result.json").write_text(json.dumps({"passed": all(cases.values()), "samples": values,
                                                     "checks": cases}, indent=2))
if not all(cases.values()):
    raise RuntimeError("Shop view GPU isolation failed")

# Non-aligned target dimensions also exercise a view smaller than its allocated buffer.
outline = u.load_asset("/Game/Characters/ResidentInteraction/M_ResidentFocusOutline")
ring = u.MaterialLibrary.create_dynamic_material_instance(world, outline)
capture.add_or_update_blendable(mid, 0.0)
capture.add_or_update_blendable(ring, 1.0)
capture.capture_source = u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
width, height = 481, 163
target = u.RenderingLibrary.create_render_target2d(world, width, height, u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
capture.texture_target = target
u.AutomationLibrary.finish_loading_before_screenshot()
edge_counts = {}
for selected in (0, 176, 191):
    ring.set_scalar_parameter_value("ResidentStencil", float(selected))
    for _ in range(3):
        capture.capture_scene()
    pixels = u.RenderingLibrary.read_render_target_raw(world, target, False)
    counts = []
    for center in (112, 176, 240, 304, 368):
        region = (pixels[y * width + x] for y in range(64, 99) for x in range(center - 29, center + 30))
        # ReadRenderTargetRaw returns byte channel values for an RGBA8 target.
        counts.append(sum(p.g - max(p.r, p.b) > 255 * .035 for p in region))
    edge_counts[selected] = counts
expected = {0: (False,) * 5, 176: (True, False, True, False, False),
            191: (False, True, False, False, False)}
ok = all((count >= 8 if visible else count == 0) for selected, flags in expected.items()
         for count, visible in zip(edge_counts[selected], flags))
(out / "gpu-outline-result.json").write_text(json.dumps({"passed": ok, "green_edge_pixels": edge_counts,
                                                        "target": [width, height]}, indent=2))
if not ok:
    raise RuntimeError("Per-target outline or occlusion failed")
