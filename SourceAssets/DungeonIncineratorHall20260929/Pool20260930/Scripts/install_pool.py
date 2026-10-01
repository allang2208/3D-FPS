"""Capture the accepted map once, then save the full room into the production catalog."""
import copy,hashlib,json,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
SAMPLE='/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
background='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not background and not globals().get('ALLOW_EDITOR_BATCH'):raise RuntimeError('Use the scoped existing-editor batch for loaded maps')
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def vec(v):return [v.x,v.y,v.z]
def path(o):return o.get_path_name().split('.')[0]
def point(v):return [v[0]*100,-v[1]*100,v[2]*100]
def box(lo,hi):
    a,b=point(lo),point(hi);return dict(min=[min(a[i],b[i]) for i in range(3)],max=[max(a[i],b[i]) for i in range(3)])
hall=read(HALL/'Config/room.json');blood=read(HALL/'MorgueBlood20260930/Config/blood.json')
mood=read(HALL/'MorgueLighting20260930/Config/lighting.json')
module_file=ROOT/'Config/module.json'
if not module_file.exists():
    world=u.EditorLoadingAndSavingUtils.load_map(SAMPLE)
    if not world:raise RuntimeError('Cannot load accepted sample before retirement')
    pieces=[];lights=[];runtime=[]
    for actor in AA.get_all_level_actors():
        label=actor.get_actor_label();tags=[str(t) for t in actor.tags]
        if isinstance(actor,u.StaticMeshActor):
            c=actor.static_mesh_component;mesh=c.static_mesh
            if not mesh or 'Incinerator.SampleOnly' in tags or 'SamplePortCaps' in mesh.get_name():continue
            p=dict(mesh=path(mesh),position=vec(actor.get_actor_location()),scale=vec(actor.get_actor_scale3d()),
                   yaw=actor.get_actor_rotation().yaw,collision=c.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION,
                   fluid=False,materials=[path(c.get_material(i)) if c.get_material(i) else '' for i in range(c.get_num_materials())],
                   cast_shadow=c.get_editor_property('cast_shadow'),source_label=label)
            p['affects_navigation']=p['collision']
            if 'Traversal.GuardrailDrop' in tags:p['guardrail_drop']=True
            if blood['receiver_tag'] in tags:p['blood_receiver']=True
            pieces.append(p)
        elif isinstance(actor,u.PointLight):
            c=actor.point_light_component
            if not c.get_editor_property('visible') or c.intensity<=0:continue
            color=c.get_light_color()
            l=dict(position=vec(actor.get_actor_location()),yaw=actor.get_actor_rotation().yaw,
                   intensity=c.intensity,radius=c.attenuation_radius,optimized_radius_cm=c.attenuation_radius,
                   color=[color.r,color.g,color.b],type='point',role='path' if label.startswith('Incinerator_B1') else 'key',
                   cast_shadows=c.cast_shadows,max_draw_distance_cm=c.max_draw_distance,fade_range_cm=c.max_distance_fade_range,
                   source_radius=c.source_radius,source_length=c.source_length,
                   indirect_lighting_intensity=c.indirect_lighting_intensity,
                   volumetric_scattering_intensity=c.volumetric_scattering_intensity)
            material=c.get_editor_property('light_function_material')
            if material:l.update(light_function=path(material),light_function_fade_distance=c.light_function_fade_distance,disabled_brightness=c.disabled_brightness)
            lights.append(l)
        elif isinstance(actor,u.DecalActor):
            c=actor.get_component_by_class(u.DecalComponent);r=actor.get_actor_rotation()
            runtime.append(dict(type='decal',position=vec(actor.get_actor_location()),yaw=r.yaw,pitch=r.pitch,roll=r.roll,
                material=path(c.get_decal_material()),decal_size=vec(c.decal_size),sort_order=c.sort_order,fade_screen_size=c.fade_screen_size))
    for group in blood['groups']:
        runtime.append(dict(type='blood',position=[0,0,0],yaw=0,material=blood['material'],
            floor_count=group['floor_count'],wall_count=group['wall_count'],scanned_size_range_cm=blood['scanned_size_range_cm'],
            floor_size_scale=blood['floor_size_scale'],surfaces=[dict(center=point(s['center_m']),normal=[s['normal'][0],-s['normal'][1],s['normal'][2]],
            axis_u=[s['axis_u'][0],-s['axis_u'][1],s['axis_u'][2]],half_size=[v*100 for v in s['half_size_m']],wall=s['wall']) for s in group['surfaces']]))
    pp=mood['postprocess']
    runtime.append(dict(type='post_process',position=point(pp['center_m']),yaw=0,extent=pp['extent_cm'],blend_radius=pp['blend_radius_cm'],priority=20,
        exposure_ev=pp['exposure_ev'],exposure_bias=pp['exposure_bias'],indirect_intensity=pp['indirect_intensity'],
        saturation=pp['saturation'],contrast=pp['contrast'],vignette=pp['vignette'],bloom=pp['bloom']))
    runtime.append(dict(type='post_process',position=[0,0,445],yaw=0,extent=[1630,1080,475],blend_radius=75,priority=10,
        exposure_ev=.2,exposure_bias=0,indirect_intensity=1,saturation=1,contrast=1,vignette=.4,bloom=.675))
    cells=[box([-14.3,-7.8,-3.9],[14.3,7.8,9.6]),box([-11.8,-10.8,-3.9],[11.8,-8.7,9.6]),
           box([-14.3,-9.,-3.9],[14.3,-7.2,9.6]),box([-14.3,7.2,-3.9],[14.3,9.,9.6]),
           box([-14.3,8.7,-3.9],[11.8,10.8,9.6]),
           box([-16.3,-2.53,-.25],[-13.7,2.53,3.8]),box([13.7,-2.53,-.25],[16.3,2.53,3.8])]
    anchors=[dict(position=point([x,y,.05]),role='incinerator_combat') for x in (-9,-4,2,8) for y in (-1.3,2.8)]
    anchors += [dict(position=point([x,y,-3.55]),role='incinerator_combat') for x,y in [(-6,0),(0,-5),(4,1),(8,-5),(-9,7)]]
    module=dict(id='AbandonedIncineratorHall',family_id='AbandonedIncineratorHall',role='room',encounter_role='special_combat',
        revision='incinerator_two_storey_pool_v1_20260930',min=[-1630,-1080,-390],max=[1630,1080,960],cells=cells,
        ports=[dict(id=p['id'],position=point(p['position']),normal=[p['normal'][0],-p['normal'][1],p['normal'][2]],width=p['width']*100,height=p['height']*100) for p in hall['ports']],
        port_pairs=[[0,1]],parts=pieces,lights=lights,runtime_actors=runtime,anchors=anchors,
        walk_mask=[box([-13.6,-2.25,-.05],[13.6,4.7,2.8]),box([-16,-1.45,-.05],[-13.6,1.45,2.8]),
                   box([13.6,-1.45,-.05],[16,1.45,2.8]),box([-8.4,-7.2,-3.65],[9,4.7,-.7]),box([-13.3,5.5,-3.65],[-5.2,10,-.7])],
        walk_polyline=[[-1600,0,5],[0,0,5],[1600,0,5]],selection=dict(chance_per_run=.3,max_per_run=1,route='Approach'))
    module_file.write_text(json.dumps(module,ensure_ascii=False,indent=2),encoding='utf-8')
else:module=read(module_file)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET) if background else u.find_object(None,TARGET+'.L_Dungeon_Randomized')
if not world:raise RuntimeError('Cannot load production map')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one production generator')
g=generators[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
backup=ROOT/'Backup';backup.mkdir(exist_ok=True)
bp=backup/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not bp.exists():bp.write_text(before,encoding='utf-8')
spawn=copy.deepcopy(next(m for m in catalog['modules'] if m['id']=='AbandonedIsolationWard')['spawn'])
spawn.update(source='DungeonIncineratorHall20260929',count=[6,8],anchor_roles=['incinerator_combat'],theme='abandoned_incinerator_morgue',sealed_encounter=True)
module['spawn']=spawn
helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for item in sorted(set(helpers['asset_paths'](module))):
    asset=u.load_class(None,item) if item.startswith('/Script/') or item.endswith('_C') else u.load_asset(item)
    if not asset:raise RuntimeError('Missing production dependency '+item)
    assets[asset.get_path_name()]=asset
module['runtime_assets']=sorted(set(helpers['asset_paths'](module['runtime_actors'])))
catalog=helpers['extend'](catalog,module)
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
packages=[p for p in dirty if 'gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Cannot save production generator packages')
(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
module_file.write_text(json.dumps(module,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,module=module['id'],room_ids=catalog['room_ids'],
    saved_packages=[p.get_name() for p in packages],parts=len(module['parts']),lights=len(module['lights']),runtime_actors=len(module['runtime_actors']),
    sample_port_caps_included=False,selection=module['selection'],tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATOR_POOL_MAP_SAVED '+TARGET,flush=True)
