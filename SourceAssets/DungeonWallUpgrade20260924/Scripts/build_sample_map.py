"""Author a separate comparison level from the existing transit module. No PIE/render."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];BASE='/Game/Dungeons/WallUpgrade20260924'
MAP=BASE+'/Preview/L_WallMaterialComparison'
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem);LE=u.get_editor_subsystem(u.LevelEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if E.does_asset_exist(MAP):
    if (ROOT/'Receipts/sample-map.json').exists():raise RuntimeError('Completed sample exists; preserve it')
    if not LE.load_level(MAP):raise RuntimeError('Cannot resume empty sample map')
    # new_level saves an empty package before authoring; recover only that empty map.
    if any(a.__class__.__name__ not in ['WorldSettings','Brush','LevelBounds'] for a in AA.get_all_level_actors()):
        raise RuntimeError('Sample contains saved actors; preserve it')
elif not LE.new_level(MAP):raise RuntimeError('Cannot create comparison map')
remap={
 '/Game/Dungeons/AtmosphereV2/Materials/M_Concrete':'MI_WallConcrete',
 '/Game/Dungeons/WallDamage20260923/Materials/MI_FabExposedBed':'MI_ExposedMortar',
 '/Game/Dungeons/WallDamage20260923/Materials/MI_FabBondingMortar':'MI_BondingMortar',
 '/Game/Dungeons/WallDamage20260923/Materials/MI_FabBrokenConcrete':'MI_BrokenConcrete'}
materials={name:u.load_asset(BASE+'/Materials/'+name) for name in remap.values()}
if not all(materials.values()):raise RuntimeError('Candidate materials not installed')
baseline={}
for path in remap:
    frozen=BASE+'/Baseline/'+path.rsplit('/',1)[1]+'_BeforeUpgrade'
    baseline[path]=u.load_asset(frozen if E.does_asset_exist(frozen) else path)
module=next(m for m in json.loads((PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').read_text())['modules'] if m['id']=='Transit')
records={'map':MAP,'production_catalog_changed':False,'groups':[],'cameras':[],'stage':'building','runtime_tested':False,'rendered':False}
def actor(cls,pos,rot=None,label=''):
    a=AA.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator())
    a.set_actor_label(label);a.set_editor_property('tags',['WallUpgradeSample']);return a
def camera(label,pos,target):
    a=actor(u.CameraActor,pos,u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),label)
    a.get_component_by_class(u.CameraComponent).set_editor_property('field_of_view',65.)
    records['cameras'].append(label);return a
def label(text,pos):
    a=actor(u.TextRenderActor,pos,u.Rotator(pitch=0,yaw=90,roll=0),text)
    c=a.get_component_by_class(u.TextRenderComponent);c.set_text(text);c.set_world_size(20)
for group,new,ox,oy,neutral in [('A_ORIGINAL',False,0,0,False),('B_UPGRADE',True,700,0,False),
                                 ('C_ORIGINAL_SIDE_LIGHT',False,0,-1100,True),('D_UPGRADE_SIDE_LIGHT',True,700,-1100,True)]:
    bound=[]
    for p in module['parts']:
        pos=p['position'];a=actor(u.StaticMeshActor,(pos[0]+ox,pos[1]+oy,pos[2]),u.Rotator(pitch=0,yaw=p['yaw'],roll=0),group+'_'+p['mesh'].rsplit('/',1)[1])
        c=a.static_mesh_component;mesh=u.load_asset(p['mesh']);c.set_static_mesh(mesh);a.set_actor_scale3d(u.Vector(*p['scale']))
        a.set_folder_path(group)
        # Keep the original baseline after the public material identities are upgraded.
        # Overrides belong only to sample components, never to shared source meshes.
        for i in range(c.get_num_materials()):
            old=c.get_material(i)
            if old:
                path=old.get_path_name().split('.')[0];name=remap.get(path)
                if name:
                    target=materials[name] if new else baseline[path]
                    c.set_material(i,target);bound.append((p['mesh'],i,target.get_path_name()))
    label(group,(ox,oy+10,320))
    for light in module['lights']:
        p=light['position'];a=actor(u.PointLight,(ox+p[0],oy+p[1],p[2]),label=group+'_OriginalFixtureLight')
        c=a.point_light_component;c.set_intensity(light['intensity']);c.set_attenuation_radius(light['radius'])
        c.set_light_color(u.LinearColor(*light['color'],1));c.set_mobility(u.ComponentMobility.MOVABLE)
    if neutral:
        pos=u.Vector(ox+75,oy-80,215);target=u.Vector(ox+155,oy-220,160)
        a=actor(u.RectLight,(pos.x,pos.y,pos.z),u.MathLibrary.find_look_at_rotation(pos,target),group+'_SideLight')
        c=a.get_component_by_class(u.RectLightComponent);c.set_intensity(120.)
        c.set_editor_property('source_width',35);c.set_editor_property('source_height',80);c.set_editor_property('attenuation_radius',420)
    for zone,z in [('Upper',205),('Mortar',95)]:
        for distance in [55,150,285]:camera(group+'_'+zone+'_'+str(distance)+'cm',(ox+155-distance,oy-160,z),(ox+155,oy-230,z))
    records['groups'].append({'label':group,'offset':[ox,oy,0],'candidate':new,'neutral_side_light':neutral,'component_overrides':bound})
# Small boards also expose the broken-section material, absent from this corridor's slots.
old_paths=list(remap)
for j,path in enumerate(old_paths):
    for k,new in enumerate([False,True]):
        a=actor(u.StaticMeshActor,(1700,150-j*160,80+k*130),label=('New_' if new else 'Old_')+remap[path])
        a.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        a.set_actor_scale3d(u.Vector(.04,1,1))
        a.static_mesh_component.set_material(0,materials[remap[path]] if new else baseline[path])
pos=u.Vector(1570,50,240);target=u.Vector(1700,-120,140)
light=actor(u.RectLight,(pos.x,pos.y,pos.z),u.MathLibrary.find_look_at_rotation(pos,target),'Boards_SideLight')
light.get_component_by_class(u.RectLightComponent).set_intensity(180.)
camera('Boards_AllSurfaces',(1350,-160,170),(1700,-160,170))
actor(u.PlayerStart,(0,-180,100),label='Sample_PlayerStart')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
# The baseline exposure is fixed for all four rooms; no changes to project lighting settings.
pp=actor(u.PostProcessVolume,(0,0,0),label='Sample_FixedExposure')
pp.set_editor_property('unbound',True);settings=pp.get_editor_property('settings')
for key,value in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),
                  ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),
                  ('override_auto_exposure_bias',True),('auto_exposure_bias',-5.)]:settings.set_editor_property(key,value)
pp.set_editor_property('settings',settings)
camera('Overview',(350,650,320),(350,-180,150))
if not LE.save_current_level():raise RuntimeError('Sample map save failed')
records['stage']='sample_map_saved';(ROOT/'Receipts/sample-map.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('WALL_UPGRADE_SAMPLE_SAVED',MAP,flush=True)
