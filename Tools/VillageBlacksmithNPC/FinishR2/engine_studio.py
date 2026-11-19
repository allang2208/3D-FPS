"""Render the saved skeletal meshes and game material assets in a transient editor world."""
import json
import math
import os
from pathlib import Path
import unreal as u

base=Path(__file__).resolve().parents[3]/'SourceAssets/VillageBlacksmithNPC20261118'
review=base/'FinishR2/Review'
stage=os.environ['SMITH_STUDIO_STAGE']
shots=json.loads((review/'camera_rig.json').read_text())
root='/Game/Characters/VillageBlacksmithNPC20261118/'
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def spawn(cls,loc=(0,0,0),rot=None):
    return actors.spawn_actor_from_class(cls,u.Vector(*loc),rot or u.Rotator(),True)
clip=u.load_asset('/Game/Characters/JasonPlayer20261003/Animations/J_MM_Idle')
components=[]
bindings={}
for part in ('Body','Head','Outfit'):
    actor=spawn(u.SkeletalMeshActor)
    comp=actor.skeletal_mesh_component
    comp.set_mobility(u.ComponentMobility.MOVABLE)
    mesh=u.load_asset(root+'SK_Smith_'+part)
    if not mesh:raise ValueError('Missing game mesh '+part)
    comp.set_skeletal_mesh_asset(mesh)
    comp.set_forced_lod(1)
    components.append(comp)
    bindings[part]=[{'slot':str(slot.material_slot_name),'material':slot.material_interface.get_path_name() if slot.material_interface else None} for slot in mesh.materials]
body=components[0]
body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
body.set_update_animation_in_editor(True)
body.play_animation(clip,False)
body.set_position(0.,False)
for comp in components[1:]:
    comp.set_leader_pose_component(body,True,False)
# No level is saved and no game session is started.
for angle,yaw,intensity in [(-42,-110,4.2),(-24,75,1.),(-32,8,1.8)]:
    sun=spawn(u.DirectionalLight,(0,0,340),u.Rotator(pitch=angle,yaw=yaw))
    sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(intensity)
    sun.light_component.set_cast_shadows(intensity>2)
sky=spawn(u.SkyLight)
sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.light_component.set_editor_property('cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
sky.light_component.set_intensity(.72)
camera=spawn(u.SceneCapture2D)
cc=camera.capture_component2d
cc.set_mobility(u.ComponentMobility.MOVABLE)
cc.capture_every_frame=False;cc.capture_on_movement=False
cc.projection_type=u.CameraProjectionMode.ORTHOGRAPHIC
cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
pp=cc.get_editor_property('post_process_settings')
for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',.38)]:
    pp.set_editor_property(k,v)
cc.set_editor_property('post_process_settings',pp)
for c in ['r.ScreenPercentage 100','r.Shadow.Virtual.Enable 0','r.TextureStreaming 0']:
    u.SystemLibrary.execute_console_command(world,c)
u.AutomationLibrary.finish_loading_before_screenshot()
rows=[]
for slug in ('portrait','workwear'):
    shot=shots[slug]
    m=shot['world_matrix']
    loc=u.Vector(*[m[i][3]*100 for i in range(3)])
    direction=u.Vector(*[-m[i][2] for i in range(3)])
    camera.set_actor_location(loc,False,True)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(loc,loc+direction),False)
    width,height=shot['pixels']
    cc.ortho_width=shot['ortho_scale']*100*min(1,width/height)
    target=u.RenderingLibrary.create_render_target2d(world,width,height,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    cc.texture_target=target
    for _ in range(4):cc.capture_scene()
    u.RenderingLibrary.export_render_target(world,target,str(review),'ue_'+stage+'_'+slug+'.png')
    rows.append({'camera':slug,'width_cm':cc.ortho_width,'world_camera_cm':loc.to_tuple(),'direction':direction.to_tuple()})
(review/('ue_'+stage+'.json')).write_text(json.dumps({'meshes':[c.get_skeletal_mesh_asset().get_path_name() for c in components],'bindings':bindings,'shots':rows,'engine':u.SystemLibrary.get_engine_version(),'pose_time':0},indent=2))
