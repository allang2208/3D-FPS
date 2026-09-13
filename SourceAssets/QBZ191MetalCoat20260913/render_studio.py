"""Render the installed QBZ assets in an isolated editor studio; no gameplay tests."""
import unreal as u,json,traceback,time,math
from pathlib import Path
O=Path(__file__).parent;OUT=O/'Preview';OUT.mkdir(exist_ok=True);D='/Game/Weapons/QBZ191/Attachments20260913'
actors=[];parts={};state={'frame':0,'step':0,'start':time.monotonic()};callback=None
def setprops(obj,**kw):
 for k,v in kw.items():obj.set_editor_property(k,v)
def spawn(cls,pos=(0,0,0),rot=None):
 a=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());actors.append(a);return a
def look(a,pos,target):a.set_actor_location_and_rotation(u.Vector(*pos),u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False,True)
def mat(name,color,metal=0.,rough=.5,hide=False):
 m=u.MaterialFactoryNew().factory_create_new(u.Material,u.get_transient_package(),name,0,None,None) if False else u.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/Weapons/QBZ191/MetalCoat20260913/Preview',u.Material,u.MaterialFactoryNew())
 if not m:m=u.load_asset('/Game/Weapons/QBZ191/MetalCoat20260913/Preview/'+name)
 L=u.MaterialEditingLibrary;L.delete_all_material_expressions(m)
 if hide:m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
 c=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.set_editor_property('constant',u.LinearColor(*color,1));L.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
 for value,prop in [(metal,u.MaterialProperty.MP_METALLIC),(rough,u.MaterialProperty.MP_ROUGHNESS)]+([(0.,u.MaterialProperty.MP_OPACITY_MASK)] if hide else []):
  n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);L.connect_material_property(n,'',prop)
 L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(m);return m
def attach(key,bone='WPN_root',pos=(0,0,0),rot=None,scale=.01):
 a=spawn(u.StaticMeshActor);c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(u.load_asset(D+'/SM_QBZ191_'+key));c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 a.attach_to_component(gun,bone,u.AttachmentRule.KEEP_RELATIVE,u.AttachmentRule.KEEP_RELATIVE,u.AttachmentRule.KEEP_RELATIVE,False)
 a.set_actor_relative_transform(u.Transform(location=u.Vector(*pos),rotation=rot.rotator() if rot else u.Rotator(),scale=u.Vector(scale,scale,scale)),False,True);parts[key]=a;return a
def configure(grip,muzzle):
 for k,a in parts.items():
  if k in ['vertical','canted','prism','angled','suppressor','brake','titanium_brake']:a.set_actor_hidden_in_game(k not in [grip,muzzle]);a.set_is_temporarily_hidden_in_editor(k not in [grip,muzzle])
def finish(error=None):
 global callback
 if callback:u.unregister_slate_post_tick_callback(callback);callback=None
 (O/('render_error.txt' if error else 'render_complete.json')).write_text(error or json.dumps({'images':[x[0] for x in shots],'renderer':'UE 5.8 installed materials and meshes; studio preview, not gameplay acceptance'},indent=2))
 u.SystemLibrary.quit_editor()
try:
 u.EditorPythonScripting.set_keep_python_script_alive(True)
 world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
 u.SystemLibrary.execute_console_command(world,'r.TextureStreaming 0')
 u.SystemLibrary.execute_console_command(world,'r.AntiAliasingMethod 2')
 u.SystemLibrary.execute_console_command(world,'r.ScreenPercentage 100')
 u.SystemLibrary.execute_console_command(world,'t.IdleWhenNotForeground 0')
 hidden=mat('M_QBZ_PreviewHidden',(0,0,0),hide=True)
 actor=spawn(u.SkeletalMeshActor);gun=actor.skeletal_mesh_component;gun.set_mobility(u.ComponentMobility.MOVABLE);asset=u.load_asset(D+'/SK_QBZ191_Manny');gun.set_skeletal_mesh_asset(asset)
 for i,slot in enumerate(asset.materials):
  name=str(slot.material_slot_name).lower()
  if any(t in name for t in ['manny','glove','sleeve','hands','magazine','flash_hider']):gun.set_material(i,hidden)
 gun.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE);gun.set_animation(u.load_asset('/Game/Weapons/QBZ191/Refined20260913/Animations/base/A_QBZ191_idle'));gun.set_position(0.,False);gun.set_update_animation_in_editor(True);gun.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 for k in ['vertical','canted','prism']:attach(k,pos=(.000688,.295,.040546),rot=u.Quat(0,0,.7071067966,.7071067657))
 attach('angled',pos=(.0471732207,-.1292048097,.0811893493),rot=u.Quat(-.0000000566,-.0002106202,.9999999385,-.0002803755))
 for k in ['suppressor','brake','titanium_brake']:attach(k)
 attach('drum','WPN_SOCKET_Magazine')
 # Bare sights keep this material study focused on the requested grip/muzzle/drum.
 for key,y,angle in [('RearSight',-.009231,0),('FrontSight',.343514,0)]:
  a=spawn(u.StaticMeshActor);c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(u.load_asset(D+'/SM_QBZ191_'+key));a.attach_to_component(gun,'WPN_root',u.AttachmentRule.KEEP_RELATIVE,u.AttachmentRule.KEEP_RELATIVE,u.AttachmentRule.KEEP_RELATIVE,False)
  a.set_actor_relative_transform(u.Transform(location=u.Vector(.000688,y,.1),rotation=u.Rotator(0,0,angle),scale=u.Vector(.01,.01,.01)),False,True)
 ground=spawn(u.StaticMeshActor,(0,12,-23));ground.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));ground.set_actor_scale3d(u.Vector(30,30,30));ground.static_mesh_component.set_material(0,mat('M_QBZ_StudioFloor',(.018,.023,.029),rough=.73))
 for pos,power,width,height,color in [((70,0,85),300.,150.,100.,(1.,.96,.9)),((-55,15,60),200.,130.,75.,(.8,.88,1.)),((0,-65,40),125.,100.,55.,(1.,1.,1.)),((100,45,18),150.,130.,75.,(1.,1.,1.))]:
  a=spawn(u.RectLight);look(a,pos,(0,15,0));c=a.get_component_by_class(u.RectLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE);c.set_intensity(power);c.set_light_color(u.LinearColor(*color,1));setprops(c,source_width=width,source_height=height,attenuation_radius=600.)
 sky=spawn(u.SkyLight);sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);sky.light_component.set_intensity(.6)
 cubemap=u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')
 if cubemap:setprops(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=cubemap)
 capture=spawn(u.SceneCapture2D);cc=capture.get_component_by_class(u.SceneCaptureComponent2D)
 rt=u.RenderingLibrary.create_render_target2d(world,2048,1152,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.025,.03,.04,1))
 setprops(cc,texture_target=rt,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=110.,always_persist_rendering_state=True)
 pp=cc.get_editor_property('post_process_settings');setprops(pp,override_auto_exposure_method=True,auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,override_auto_exposure_bias=True,auto_exposure_bias=-3.,override_auto_exposure_apply_physical_camera_exposure=True,auto_exposure_apply_physical_camera_exposure=False,override_motion_blur_amount=True,motion_blur_amount=0.,override_vignette_intensity=True,vignette_intensity=0.,override_bloom_intensity=True,bloom_intensity=0.);cc.set_editor_property('post_process_settings',pp)
 shots=[('01_overview',(100,55,35),(0,13,-.5),110.,'angled','titanium_brake'),('02_grip_drum',(85,6,23),(0,20,-5),56.,'vertical','suppressor'),('03_muzzle',(85,75,30),(0,48,6),45.,'canted','brake'),('04_angled',(85,4,24),(0,20,-3),57.,'angled','titanium_brake')]
 def tick(dt):
  global rt
  try:
   if time.monotonic()-state['start']<15:return
   state['frame']+=1;f=state['frame']
   if f==30:
    root=gun.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_WORLD);q=root.rotation;actor.set_actor_rotation(u.Quat(-q.x,-q.y,-q.z,q.w).rotator(),False)
    root=gun.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_WORLD);actor.set_actor_location(-root.translation,False,True)
   if f>=50:
    n=state['step'];shot=shots[n]
    if f==50:
     configure(shot[4],shot[5]);look(capture,shot[1],shot[2]);cc.set_editor_property('ortho_width',shot[3])
     rt=u.RenderingLibrary.create_render_target2d(world,2048,1152,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.025,.03,.04,1));cc.set_editor_property('texture_target',rt);cc.set_editor_property('camera_cut_this_frame',True)
    if 55<=f<150:cc.capture_scene()
    if f==56:cc.set_editor_property('camera_cut_this_frame',False)
    if f>=150:
     u.RenderingLibrary.export_render_target(world,rt,str(OUT),shot[0]+'.png');state['step']+=1
     if state['step']==len(shots):finish();return
     state['frame']=49
  except Exception:finish(traceback.format_exc())
 callback=u.register_slate_post_tick_callback(tick)
except Exception:finish(traceback.format_exc())
