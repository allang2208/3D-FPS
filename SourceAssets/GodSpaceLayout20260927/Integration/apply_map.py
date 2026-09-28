"""Persist the approved floating hub, reusing gameplay actors and existing clouds. No PIE."""
from pathlib import Path
from collections import defaultdict
import hashlib, json, math, shutil
import unreal as u

ROOT=Path(__file__).parent;PROJECT=ROOT.parents[2]
DATA=json.loads((ROOT/'placements.json').read_text(encoding='utf8'))
MAP='/Game/GameMaps/DayNight_Lighting';DEST='/Game/Props/GodSpaceLayout20260927'
TAG='GodSpace.LayoutV1';OFF=DATA['world_offset_cm']
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('End PIE before saving the approved hub layout')
if not globals().get('RESUME_OWNED_MAP',False) and any(p.get_path_name()==MAP for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
    raise RuntimeError('Hub has unsaved edits; preserve the editor state')
world=editor.get_editor_world() if editor else None
if not world or world.get_path_name().split('.')[0]!=MAP:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve the other unsaved map before switching')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
if not world:raise RuntimeError('Hub could not load')
api=u.get_editor_subsystem(u.EditorActorSubsystem)
actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
report={'map':MAP,'saved':False,'removed':[],'new_static_actors':0,'clusters':[],'preserved_gameplay':[],'tested':False}
source=PROJECT/'Content/GameMaps/DayNight_Lighting.umap'
backup=PROJECT/'trash/godspace-layout-20260927/Before/Content/GameMaps/DayNight_Lighting.umap'
if not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    (ROOT/'Receipts/hub-backup.json').write_text(json.dumps({'source':str(source),'backup':str(backup),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'reason':'Approved floating hub layout replacement'},indent=2),encoding='utf8')

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing layout dependency '+path)
    return obj
def pos(local):return u.Vector(*(local[i]*100+OFF[i] for i in range(3)))
def mark(a,label,role='Architecture'):
    a.set_actor_label(label)
    a.set_folder_path('GodSpace/'+role)
    a.tags=list(dict.fromkeys(list(a.tags)+[u.Name(TAG)]))
def spawn(cls,where,yaw=0):
    a=api.spawn_actor_from_class(cls,where,u.Rotator(pitch=0,yaw=yaw,roll=0))
    if not a:raise RuntimeError('Could not create '+str(cls))
    return a
def anchor(label,tag,where,yaw=0):
    a=spawn(u.TargetPoint,where,yaw);mark(a,label,'Anchors');a.tags=list(a.tags)+[u.Name(tag)];return a
def place(a,entry):
    mesh=load(entry['mesh']);b=mesh.get_bounding_box();s=entry['scale'];r=math.radians(entry['yaw'])
    cx=(b.min.x+b.max.x)*.5*s[0];cy=(b.min.y+b.max.y)*.5*s[1]
    p=pos(entry['location_m']);p.x-=cx*math.cos(r)-cy*math.sin(r);p.y-=cx*math.sin(r)+cy*math.cos(r);p.z-=b.min.z*s[2]
    a.set_actor_transform(u.Transform(location=p,rotation=u.Rotator(pitch=0,yaw=entry['yaw'],roll=0),scale=u.Vector(*s)),False,True)
    return mesh

# Resolve dependencies before changing the loaded map. Saved prefab/player inventory
# data is deliberately untouched: the service court is aligned to its existing area.
meshes={e['mesh']:load(e['mesh']) for e in DATA['placements']}
new_meshes={e['name']:load(DEST+'/Meshes/'+e['name']) for e in DATA['new_meshes']}
cloud_material=load(DEST+'/Materials/MI_GodSpaceCloudSea')
# The shared rail used to contain visual triangles but no simple collision.
# Author its fitted box before creating the perimeter instances.
rail_script=ROOT/'ensure_rail_collision.py'
exec(compile(rail_script.read_text(encoding='utf8'),str(rail_script),'exec'),{'__file__':str(rail_script)})
fountain=next(a for a in actors if a.get_class().get_name()=='ColdSteelFountain')
altar=next(a for a in actors if a.actor_has_tag('ColdSteel.ExpeditionAltar'))
sky=next(a for a in actors if a.get_components_by_class(u.SkyAtmosphereComponent))

for a in actors:
    if a in [fountain,altar,sky] or a.get_class().get_name()=='BronzeTorch':continue
    tags={str(t) for t in a.tags}
    architecture=(a.get_class()==u.StaticMeshActor.static_class() and any(c.static_mesh and c.static_mesh.get_path_name().startswith('/Game/Props/RomanColumn20260915/') for c in a.get_components_by_class(u.StaticMeshComponent)))
    obsolete=TAG in tags or 'ColdSteel.MainPlaza' in tags or a.get_actor_label()=='Floor' or architecture or tags.intersection({'ScenePortal.WaterLink','ScenePortal.GrassLink'})
    if obsolete:
        label=a.get_actor_label()
        if not api.destroy_actor(a):raise RuntimeError('Could not remove old layout '+label)
        report['removed'].append(label)

groups=defaultdict(list)
for e in DATA['placements']:
    if 'SM_FountainPolishedV9' in e['mesh']:
        place(fountain,e);mark(fountain,'GodSpace_Fountain','Gameplay');report['preserved_gameplay'].append(fountain.get_path_name());continue
    if 'SM_SquareAltar' in e['mesh']:
        place(altar,e);mark(altar,'GodSpace_ExpeditionAltar','Gameplay');report['preserved_gameplay'].append(altar.get_path_name());continue
    a=spawn(u.StaticMeshActor,pos(e['location_m']));c=a.static_mesh_component
    c.set_static_mesh(meshes[e['mesh']]);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll');c.set_editor_property('generate_overlap_events',False)
    place(a,e);mark(a,'GodSpace_'+e['label'].replace(' ','_'))
    a.tags=list(a.tags)+[u.Name('ColdSteel.MainPlaza.Generated')]
    if 'SM_MarbleFloorTiles' in e['mesh']:
        c.set_forced_lod_model(2);c.set_cast_shadow(False)
    else:
        policy=u.PlazaInstanceTools.cluster_policy(a)
        if policy:
            p=a.get_actor_location();key=(math.floor(p.x/1600),math.floor(p.y/1600),hashlib.sha256(policy.encode()).hexdigest()[:12])
            groups[key].append(a)
    report['new_static_actors']+=1
for key,sources in groups.items():
    if len(sources)<2:continue
    combined=u.PlazaInstanceTools.create_plaza_cluster(sources,'GodSpace_Instances_%d_%d_%s'%key)
    if not combined:raise RuntimeError('Could not serialize instance group '+str(key))
    mark(combined,combined.get_actor_label())
    for a in sources:
        if not api.destroy_actor(a):raise RuntimeError('Could not retire grouped actor')
    report['clusters'].append({'label':combined.get_actor_label(),'instances':len(sources)})

for name,mesh in new_meshes.items():
    a=spawn(u.StaticMeshActor,u.Vector(*OFF));c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
    mark(a,name.replace('SM_',''),'Backdrop' if name.endswith('Ocean') else 'Architecture')
    if name=='SM_GodSpaceStructure':c.set_collision_profile_name('BlockAll')
    else:
        c.set_collision_profile_name('NoCollision');c.set_editor_property('generate_overlap_events',False)
        if name.endswith('Ocean'):
            c.set_cast_shadow(False);c.set_editor_property('affect_distance_field_lighting',False)
            c.set_editor_property('visible_in_ray_tracing',False)
            c.set_editor_property('receives_decals',False);a.set_actor_tick_enabled(False)
            a.tags=list(a.tags)+[u.Name('GodSpace.VisualOnlyOcean')]
    c.set_editor_property('generate_overlap_events',False)

starts=[a for a in actors if isinstance(a,u.PlayerStart)]
for a in starts:
    a.set_actor_location(pos([13,-38,1.25]),False,True)
    a.set_actor_rotation(u.Rotator(pitch=0,yaw=math.degrees(math.atan2(57,-13)),roll=0),True)
    a.set_actor_label('GodSpace_PlayerStart')
anchor('GodSpace_HillsPortalAnchor','GodSpace.HillsPortalAnchor',pos(DATA['portal_local_m']),180)
anchor('GodSpace_WarehouseAnchor','GodSpace.WarehouseAnchor',u.Vector(*DATA['warehouse_world_cm']),0)

# Keep the existing dynamic torches and day/night behavior; only their placements change.
col=sorted([a for a in actors if a.get_class().get_name()=='BronzeTorch' and a.get_actor_label().startswith('ColonnadeTorch')],key=lambda a:a.get_actor_label())
for a,p in zip(col,[(-34.6,-28,1.9),(-34.6,-20,1.9),(-34.6,30,1.9),(34.6,-28,1.9),(34.6,-20,1.9),(34.6,30,1.9)]):
    a.set_actor_location(pos(p),False,True);a.set_folder_path('GodSpace/Gameplay')
for a in actors:
    if a.get_class().get_name()=='BronzeTorch' and a.get_actor_label().startswith('PavilionTorch'):
        original=next(r for r in json.loads((ROOT/'saved_hub_inputs.json').read_text(encoding='utf8')) if r['label']==a.get_actor_label())
        p=u.Vector(*original['transform']['location']);p.x+=-6150;p.y+=400;a.set_actor_location(p,False,True);a.set_folder_path('GodSpace/Gameplay')
    if isinstance(a,u.NavMeshBoundsVolume):
        old_center,old_extent=a.get_actor_bounds(False)
        scale=a.get_actor_scale3d()
        a.set_actor_scale3d(u.Vector(scale.x*4300/max(old_extent.x,1),scale.y*5100/max(old_extent.y,1),scale.z*1200/max(old_extent.z,1)))
        a.set_actor_location(u.Vector(OFF[0],OFF[1],800),False,True)

# Persist the Blueprint-owned cloud settings too, so construction keeps the sea.
config_file=ROOT/'configure_cloud_sea.py';config={'__file__':str(config_file)}
exec(compile(config_file.read_text(encoding='utf8'),str(config_file),'exec'),config)
config['apply'](sky,cloud_material)
for fog in sky.get_components_by_class(u.ExponentialHeightFogComponent):
    fog.set_world_location(u.Vector(OFF[0],OFF[1],-70000),False,True)
    fog.set_fog_density(.003)
if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Hub save failed')
report.update(saved=True,cloud_material=cloud_material.get_path_name(),cloud_bottom_relative_m=-600,cloud_top_relative_m=-280,atmosphere_ground_z_cm=-150000,world_offset_cm=OFF)
(ROOT/'Receipts/map.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('GODSPACE_MAP_SAVED '+json.dumps({'removed_old_actors':len(report['removed']),'placed_static_pieces':report['new_static_actors'],'instance_groups':len(report['clusters']),'gameplay_actors_preserved':len(report['preserved_gameplay'])}))
