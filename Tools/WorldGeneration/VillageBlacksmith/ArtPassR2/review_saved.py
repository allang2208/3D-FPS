"""Read saved assets and capture the actual furnished village in an offscreen editor world."""
import json,math
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
LEVEL='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2'
E=u.EditorAssetLibrary;S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report={'assets':[],'views':[],'gameplay_started':False,'capture_scope':'Saved village sublevel, temporary review lighting; no gameplay or live seeded terrain', 'errors':[]}
for row in json.loads((OUT/'model-manifest.json').read_text())['assets']:
    mesh=u.load_asset(DEST+'/Meshes/'+row['name'])
    if not mesh:raise RuntimeError('Saved mesh missing '+row['name'])
    b=mesh.get_bounding_box();span=b.max-b.min
    expected=[row['bounds_blender_cm'][1][i]-row['bounds_blender_cm'][0][i] for i in range(3)]
    delta=max(abs(a-b) for a,b in zip([span.x,span.y,span.z],expected))
    slots=list(mesh.static_materials)
    item={'mesh':mesh.get_path_name(),'size_cm':[span.x,span.y,span.z],'lods':S.get_lod_count(mesh),'collision_boxes':S.get_simple_collision_count(mesh),
          'size_error_cm':delta,'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in slots],
          'opaque':all(s.material_interface.get_base_material().blend_mode==u.BlendMode.BLEND_OPAQUE for s in slots),
          'instance_usage':all(s.material_interface.get_base_material().get_editor_property('used_with_instanced_static_meshes') for s in slots)}
    report['assets'].append(item)
    if item['lods']!=3 or delta>.05 or not all(item['materials']) or not item['opaque'] or not item['instance_usage']:report['errors'].append(item['mesh'])
(OUT/'saved-assets-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['errors']:raise RuntimeError('Saved asset contract '+str(report['errors']))
world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
original=list(actors.get_all_level_actors());helpers=[]
def spawn(kind,point=(0,0,0),rot=None):
    actor=actors.spawn_actor_from_class(kind,u.Vector(*point),rot or u.Rotator(),transient=True)
    if not actor:raise RuntimeError('Spawn review actor')
    helpers.append(actor);return actor
floor=spawn(u.StaticMeshActor,(0,0,-7));floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));floor.set_actor_scale3d(u.Vector(130,110,.10))
for pitch,yaw,power in [(-38,-35,4.),(-45,135,1.5)]:
    sun=spawn(u.DirectionalLight,(0,0,2000),u.Rotator(pitch=pitch,yaw=yaw));sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);sun.light_component.set_intensity(power);sun.light_component.set_cast_shadows(power>2)
sky=spawn(u.SkyLight);sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);sky.light_component.source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP
sky.light_component.cubemap=u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap');sky.light_component.set_intensity(1.)
capture=spawn(u.SceneCapture2D);capture.root_component.set_mobility(u.ComponentMobility.MOVABLE)
cc=capture.capture_component2d;cc.capture_every_frame=False;cc.capture_on_movement=False;cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.fov_angle=70
rt=u.RenderingLibrary.create_render_target2d(world,1600,1000,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB);cc.texture_target=rt
pp=cc.get_editor_property('post_process_settings')
for key,value in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',.1)]:pp.set_editor_property(key,value)
cc.set_editor_property('post_process_settings',pp)
u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.Enable 0')
output=OUT/'UEPreviews';output.mkdir(exist_ok=True)
def house_point(p):
    a=math.radians(178);x,y,z=p
    return u.Vector(-3200+x*math.cos(a)-y*math.sin(a),-900+x*math.sin(a)+y*math.cos(a),z+4)
def state(repaired):
    for actor in original:
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            tags=[str(t) for t in comp.component_tags]
            if 'VillageShop.Ruined' in tags:comp.set_visibility(not repaired,True);comp.set_hidden_in_game(repaired,True)
            if 'VillageShop.Repaired' in tags:comp.set_visibility(repaired,True);comp.set_hidden_in_game(not repaired,True)
def shot(name,eye,target):
    capture.set_actor_location(eye,False,True);capture.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,target),False)
    if not u.ApartmentExteriorAuthoringTools.bake_city_reflection(world,[floor],DEST+'/ReviewScratch/Warm',eye,64):raise RuntimeError('Renderer preparation failed')
    for i in range(4):cc.capture_scene()
    u.RenderingLibrary.export_render_target(world,rt,str(output),name+'.png')
    report['views'].append({'name':name,'eye':[eye.x,eye.y,eye.z],'target':[target.x,target.y,target.z]})
    u.log('VILLAGE_ART_VIEW '+name)
try:
    state(False)
    shot('01-blacksmith-ruined',house_point((70,-940,240)),house_point((-80,-150,210)))
    shot('02-workshop-interior',house_point((-80,-230,178)),house_point((90,155,90)))
    state(True)
    shot('03-blacksmith-repaired',house_point((70,-940,240)),house_point((-80,-150,210)))
    shot('04-workshop-repaired',house_point((-80,-230,178)),house_point((90,155,90)))
    # Review a real placed bed, including its local wall/floor context.
    beds=[]
    for actor in original:
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            if comp.static_mesh and comp.static_mesh.get_name()=='SM_VillageTimberBed':
                for i in range(comp.get_instance_count()):beds.append(comp.get_instance_transform(i,True))
    if beds:
        t=beds[0];shot('05-furnished-home',u.MathLibrary.transform_location(t,u.Vector(180,-230,150)),u.MathLibrary.transform_location(t,u.Vector(0,0,40)))
    report['placed_beds']=len(beds)
finally:
    for actor in reversed(helpers):actors.destroy_actor(actor)
    # Review state was changed only in memory. Never save temporary lights or repaired-state visibility.
    (OUT/'scene-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
