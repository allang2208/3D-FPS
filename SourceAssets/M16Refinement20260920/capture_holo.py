"""Render the installed optic through its actual UE glass; isolated transient actors."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;sub=u.get_editor_subsystem(u.EditorActorSubsystem);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();actors=[]
stage=u.Vector(0,0,100000)
def spawn(cls,offset):
 a=sub.spawn_actor_from_class(cls,stage+u.Vector(*offset));actors.append(a);return a
def setprops(obj,**props):
 for k,v in props.items():obj.set_editor_property(k,v)
try:
 m=u.new_object(u.Material);L=u.MaterialEditingLibrary;m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 pos=L.create_material_expression(m,u.MaterialExpressionWorldPosition);code=L.create_material_expression(m,u.MaterialExpressionCustom);code.set_editor_property('code','float k=fmod(abs(floor(P.y/1.5)+floor(P.z/1.5)),2);return lerp(float3(.08,.32,.85),float3(.85,.7,.12),k);');code.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3);pin=u.CustomInput();pin.set_editor_property('input_name','P');code.set_editor_property('inputs',[pin]);L.connect_material_expressions(pos,'',code,'P');L.connect_material_property(code,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.recompile_material(m)
 plane=spawn(u.StaticMeshActor,(6,0,5.1753));c=plane.static_mesh_component;c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,m);plane.set_actor_scale3d(u.Vector(.005,.15,.15))
 optic=spawn(u.StaticMeshActor,(0,0,0));oc=optic.static_mesh_component;oc.set_static_mesh(u.load_asset('/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_holographic'))
 light=spawn(u.RectLight,(-15,7,17));light.set_actor_rotation(u.MathLibrary.find_look_at_rotation(light.get_actor_location(),stage+u.Vector(0,0,4)),False);lc=light.get_component_by_class(u.RectLightComponent);lc.set_intensity(.25);setprops(lc,source_width=20.,source_height=20.,attenuation_radius=80.)
 capture=spawn(u.SceneCapture2D,(-24,0,5.175324));capture.set_actor_rotation(u.Rotator(),False);cc=capture.get_component_by_class(u.SceneCaptureComponent2D)
 rt=u.RenderingLibrary.create_render_target2d(world,800,650,u.TextureRenderTargetFormat.RTF_RGBA8)
 setprops(cc,texture_target=rt,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,capture_every_frame=False,capture_on_movement=False,fov_angle=23.,always_persist_rendering_state=True)
 pp=cc.get_editor_property('post_process_settings');setprops(pp,override_auto_exposure_method=True,auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,override_auto_exposure_bias=True,auto_exposure_bias=0.,override_auto_exposure_apply_physical_camera_exposure=True,auto_exposure_apply_physical_camera_exposure=False,override_bloom_intensity=True,bloom_intensity=.1,override_motion_blur_amount=True,motion_blur_amount=0.,override_vignette_intensity=True,vignette_intensity=0.);cc.set_editor_property('post_process_settings',pp)
 cc.capture_scene();u.RenderingLibrary.export_render_target(world,rt,str(O),'ue_holographic_glass.png')
 print('M16_GLASS_CAPTURE_SAVED')
finally:
 for a in reversed(actors):sub.destroy_actor(a)
