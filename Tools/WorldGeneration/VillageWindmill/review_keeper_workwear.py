"""Photograph the saved keeper in a transient world of the private review project."""
import json
import os
from pathlib import Path
import unreal as u

host = Path(os.environ["KEEPER_STUDIO"]).resolve()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != host:
    raise RuntimeError("This review only runs in the keeper studio")
out = Path(os.environ["KEEPER_REVIEW"])
version = os.environ["KEEPER_REVISION"]
world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)


def spawn(kind, xyz, rot=None):
    return actors.spawn_actor_from_class(kind, u.Vector(*xyz), rot or u.Rotator(), True)


root = "/Game/WorldGeneration/TemperateHills/AbandonedVillage/MillKeeper/"
mesh = u.load_asset(root+"SK_MillKeeper")
body = spawn(u.SkeletalMeshActor, (0,0,0)).skeletal_mesh_component
body.set_mobility(u.ComponentMobility.MOVABLE)
body.set_skeletal_mesh_asset(mesh)
body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
body.set_update_animation_in_editor(True)
body.play_animation(u.load_asset(root+"A_MillKeeper_Idle"), False)
body.set_position(.6, False)
body.set_forced_lod(1)
board = spawn(u.StaticMeshActor, (0,-120,82))
board.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
board.static_mesh_component.set_static_mesh(u.load_asset("/Engine/BasicShapes/Cube"))
board.set_actor_scale3d(u.Vector(18,.08,7))
background = board.static_mesh_component.create_dynamic_material_instance(0,u.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
background.set_vector_parameter_value("Color",u.LinearColor(.095,.092,.086,1))
lights = []
for pitch,yaw,power in [(-32,-145,3.6),(-12,-45,1.2),(-48,76,1.6)]:
    light = spawn(u.DirectionalLight,(0,0,220),u.Rotator(pitch=pitch,yaw=yaw)).light_component
    light.set_mobility(u.ComponentMobility.MOVABLE)
    light.set_intensity(power)
    light.set_cast_shadows(False)
    lights.append(light)
sky = spawn(u.SkyLight,(0,0,0)).light_component
sky.set_mobility(u.ComponentMobility.MOVABLE)
sky.set_editor_property("source_type",u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_editor_property("cubemap",u.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
sky.set_intensity(.62)
camera = spawn(u.SceneCapture2D,(0,120,90))
cap = camera.capture_component2d
cap.capture_every_frame = cap.capture_on_movement = False
cap.capture_source = u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
pp = cap.get_editor_property("post_process_settings")
for field,val in {"auto_exposure_method":u.AutoExposureMethod.AEM_MANUAL,
    "auto_exposure_apply_physical_camera_exposure":False,"auto_exposure_bias":.35,
    "vignette_intensity":0.,"motion_blur_amount":0.,"bloom_intensity":0.}.items():
    pp.set_editor_property("override_"+field,True)
    pp.set_editor_property(field,val)
cap.set_editor_property("post_process_settings",pp)
for cmd in ("r.TextureStreaming 0","r.ScreenPercentage 100","r.Shadow.Virtual.Enable 0"):
    u.SystemLibrary.execute_console_command(world,cmd)
target = u.RenderingLibrary.create_render_target2d(world,960,1080,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap.texture_target = target
u.AutomationLibrary.finish_loading_before_screenshot()
for label,xyz,aim,fov in [
        ("front",(19,145,84),(0,3,62),32.5),
        ("side",(-103,114,78),(0,3,60),31.5),
        ("whole",(25,244,102),(0,1,81),39.),
        ("lod2",(19,145,84),(0,3,62),32.5),
        ("lod3",(19,145,84),(0,3,62),32.5),
        ("lod4",(19,145,84),(0,3,62),32.5),
        ("lamplight",(12,114,84),(0,8,64),28.)]:
    body.set_forced_lod(int(label[-1]) if label.startswith("lod") else 1)
    if label == "lamplight":
        lights[0].set_light_color(u.LinearColor(1.,.57,.31,1.))
        lights[1].set_intensity(.42)
        sky.set_intensity(.35)
    eye = u.Vector(*xyz)
    camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,u.Vector(*aim)),False,False)
    cap.fov_angle = fov
    for _ in range(4):
        cap.capture_scene()
    u.RenderingLibrary.export_render_target(world,target,str(out),f"{version}-{label}.png")
(out/f"{version}-slots.json").write_text(json.dumps({str(s.material_slot_name):
    s.material_interface.get_path_name() for s in mesh.materials if s.material_interface},indent=2))
subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
sections={}
for lod in range(subsystem.get_lod_count(mesh)):
    sections[lod]=[subsystem.get_lod_material_slot(mesh,lod,i) for i in range(subsystem.get_num_sections(mesh,lod))]
(out/f"{version}-sections.json").write_text(json.dumps(sections,indent=2))
