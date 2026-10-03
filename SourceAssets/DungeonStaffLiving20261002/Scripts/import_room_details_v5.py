"""Build and save the V5 room details in the four existing owned sample maps."""
import json,hashlib,re,shutil,sys
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'RoomDetailsV5'
if json.loads((ROOT/'Config/room.json').read_text('utf8')).get('wall_inset_revision',0)>=6:
    current=ROOT/'Scripts/import_wall_inset_v6.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
CFG=json.loads((OUT/'Authored/room-detailed.json').read_text('utf8'))
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']+'/RoomDetailsV5'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json';report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},materials=[],backups=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False,rewards_deferred=True,random_pool_registered=False)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
sys.path.insert(0,str(ROOT/'Scripts'))
from build_room_details_materials_v5 import build_materials
report['materials']=build_materials(ROOT,BASE);record()
# Share the established FBX, UCX, tangent and full Nanite fallback build policy.
v4=ROOT/'Scripts/import_scene_polish_v4.py';code=v4.read_text('utf8')
exec(compile(code[code.index('u.SystemLibrary.execute_console_command'):code.index('AA=u.get_editor_subsystem')],str(v4),'exec'))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
container_class=u.load_class(None,'/Script/FPSGAME.ColdSteelSceneContainer')
layout_class=u.load_class(None,'/Script/FPSGAME.StaffDormitoryLayout')
if not container_class or not layout_class:raise RuntimeError('Native build required before integration')
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
def owned(a):return 'StaffLiving.Subject' in [str(t) for t in a.tags]
def loc(p,off):return u.Vector((p[0]+off[0])*100,-(p[1]+off[1])*100,(p[2]+off[2])*100)
def rot(p):return u.Rotator(pitch=0,yaw=-p['yaw_blender_deg'],roll=0)
def named(a,rid,ident,extra=()):
    a.set_actor_label('StaffSubject_'+rid+'_'+ident)
    a.set_editor_property('tags',[u.Name(t) for t in ['StaffLiving.Subject',rid,*extra]])
    a.set_folder_path('StaffLiving/'+rid);return a
def shared(proto):
    if proto in MAN['prototypes']:
        name=MAN['prototypes'][proto];return meshes[name],items[name]['collision']
    if proto in ('WashBasin','Mirror'):
        path=CFG['ue_base']+'/ScenePolishV4/Meshes/SM_Staff_'+proto+'_V4'
    else:path=CFG['ue_base']+'/Meshes/SM_Staff_'+proto
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing existing fixture '+path)
    return mesh,proto not in ('Mirror','LampFixture')
def static(p,off,rid,movable=False):
    mesh,collision=shared(p['prototype'])
    a=named(AA.spawn_actor_from_class(u.StaticMeshActor,loc(p['position'],off),rot(p)),rid,p['id'])
    c=a.static_mesh_component;c.set_static_mesh(mesh)
    c.set_mobility(u.ComponentMobility.MOVABLE if movable else u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision');return a
def replace_label(actors,label):
    if label in actors:AA.destroy_actor(actors.pop(label))
baize=u.load_asset(BASE+'/Materials/MI_Staff_BaizeRelief_V5')
outline_path=json.loads((ROOT/'ScenePolishV4/install.json').read_text('utf8'))['outline']
outline=u.load_asset(outline_path)
if not outline:raise RuntimeError('Missing accepted focus-outline material')
felt_overrides={}
targets=[(CFG['maps'][r['id']],[r],[[0,0,0]]) for r in CFG['rooms']]
targets.append((CFG['sample_map'],CFG['rooms'],CFG['preview_placements_m']))
for target,rooms,offsets in targets:
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load owned staff map '+target)
    actors={a.get_actor_label():a for a in AA.get_all_level_actors() if owned(a)};changed=[];added=[]
    for room,off in zip(rooms,offsets):
        rid=room['id'];prefix='StaffSubject_'+rid+'_'
        # Only the old green floor-box placements are removed; the reusable mesh remains.
        for label in list(actors):
            if label.startswith(prefix+'PersonalBox_'):replace_label(actors,label)
        keys={'WaterDispenser','LaundryBasket'}
        if rid=='StaffRecreation':
            keys.update(('KitchenCounterTop','TableTennisPaddle','CoffeeMachine','ElectricKettle','BathroomShell','Toilet'))
            for label in list(actors):
                if label.startswith(prefix+'Refrigerator'):replace_label(actors,label)
            for k in ('KitchenCounter','KitchenCounterTop','Chair'):
                replace_label(actors,prefix+k+'_Instances')
        replacements=[p for p in room['furniture'] if p['prototype'] in keys or (rid=='StaffRecreation' and p['id'] in ('BathroomSink','BathroomMirror','BathroomLamp'))]
        for k in keys:replace_label(actors,prefix+k+'_Instances')
        for p in replacements:
            replace_label(actors,prefix+p['id']);static(p,off,rid);changed.append(p['id'])
        if rid=='StaffChangingShowers':
            for a in actors.values():
                if isinstance(a,u.ColdSteelSceneContainer) and rid in [str(t) for t in a.tags]:
                    tags=[str(t) for t in a.tags]
                    if 'ColdSteel.SceneContainer.RandomOpen' not in tags:tags.append('ColdSteel.SceneContainer.RandomOpen')
                    a.set_editor_property('tags',[u.Name(t) for t in tags])
        if rid!='StaffRecreation':continue
        for a in actors.values():
            if not a.get_actor_label().startswith(prefix+'BilliardTable'):continue
            for c in a.get_components_by_class(u.StaticMeshComponent):
                mesh=c.get_editor_property('static_mesh')
                if not mesh:continue
                overrides=[]
                for i,slot in enumerate(mesh.get_editor_property('static_materials')):
                    key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
                    if key=='RS_Felt':c.set_material(i,baize)
                    material=c.get_material(i);overrides.append(material.get_path_name() if material else '')
                felt_overrides[mesh.get_path_name().split('.')[0]]=overrides
        for spec in MAN['containers']:
            label=prefix+spec['id'];a=actors.get(label)
            if a and not isinstance(a,u.ColdSteelSceneContainer):replace_label(actors,label);a=None
            if not a:a=AA.spawn_actor_from_class(container_class,loc(spec['position'],off),rot(spec))
            a.set_actor_location_and_rotation(loc(spec['position'],off),rot(spec),False,True)
            tags=['ColdSteel.SceneContainer']+(['ColdSteel.SceneContainer.RandomOpen'] if spec['random_open'] else [])
            named(a,rid,spec['id'],tags);a.set_folder_path('StaffLiving/'+rid+'/SearchContainers')
            a.set_editor_property('container_id',spec['container_id']);a.set_editor_property('caption',spec['caption'])
            a.set_editor_property('storage_pages',1);a.set_editor_property('opened_yaw',100.)
            a.set_editor_property('opening_motion',u.ColdSteelContainerMotion.SWING)
            a.body.set_mobility(u.ComponentMobility.MOVABLE);a.door_hinge.set_mobility(u.ComponentMobility.MOVABLE)
            a.body.set_static_mesh(u.load_asset(spec['body']));a.door.set_static_mesh(u.load_asset(spec['door']))
            a.door_hinge.set_relative_location(u.Vector(*spec['hinge_cm']),False,False)
            a.door_hinge.set_relative_rotation(u.Rotator(),False,False)
            a.body.set_collision_profile_name('BlockAll');a.door.set_collision_profile_name('NoCollision')
            for c in (a.body,a.door):
                c.set_mobility(u.ComponentMobility.MOVABLE);c.set_render_custom_depth(False);c.set_custom_depth_stencil_value(201)
            added.append(spec['container_id'])
        chairs=[]
        for p in MAN['chair_poses']:
            replace_label(actors,prefix+p['id']);p=dict(p,prototype='Chair');a=static(p,off,rid,True)
            named(a,rid,p['id'],['StaffDormitory.LayoutSlot.'+p['id']]);chairs.append(a)
        manager_id='ChairVariantsV5';replace_label(actors,prefix+manager_id)
        manager=named(AA.spawn_actor_from_class(layout_class,loc([0,0,0],off)),rid,manager_id)
        manager.set_editor_property('layout_json',json.dumps(MAN['chair_layout'],ensure_ascii=False,separators=(',',':')))
        manager.set_editor_property('layout_actors',chairs);manager.set_editor_property('random_seed',-1)
        replace_label(actors,prefix+'Light_Bathroom')
        light=named(AA.spawn_actor_from_class(u.PointLight,loc([12.20,6.13,2.61],off)),rid,'Light_Bathroom',['Dungeon.Light.Fill'])
        c=light.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(380.)
        c.set_editor_property('attenuation_radius',330.);c.set_editor_property('cast_shadows',False)
        c.set_editor_property('max_draw_distance',1400.);c.set_editor_property('max_distance_fade_range',300.)
        c.set_editor_property('indirect_lighting_intensity',.10);c.set_light_color(u.LinearColor(.79,.87,.82,1))
    # The independent recreation map previously had no searchable scenery and
    # therefore no outline volume. Give its new containers the same soft effect.
    if any(r['id']=='StaffRecreation' for r in rooms):
        pp=next((a for a in AA.get_all_level_actors() if owned(a) and isinstance(a,u.PostProcessVolume)
            and 'ColdSteel.SceneContainer.Outline' in [str(t) for t in a.tags]),None)
        if not pp:pp=AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
        pp.set_actor_label('StaffSubject_ContainerOutline_V1');pp.set_folder_path('StaffLiving/Environment')
        pp.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name('ColdSteel.SceneContainer.Outline')])
        pp.set_editor_property('unbound',True);pp.set_editor_property('priority',1.)
        settings=pp.get_editor_property('settings');blend=u.WeightedBlendable()
        blend.set_editor_property('weight',1.);blend.set_editor_property('object',outline)
        blends=u.WeightedBlendables();blends.set_editor_property('array',[blend])
        settings.set_editor_property('weighted_blendables',blends);pp.set_editor_property('settings',settings)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',updated_static_placements=changed,new_containers=added,
        random_open_probability=.32,chair_variants=4 if added else 0,baize_overrides=felt_overrides);record()
    u.log('STAFF_ROOM_DETAILS_V5_MAP_SAVED '+target)
for filename in ('room.json','modules-draft.json'):shutil.copy2(ROOT/'Config'/filename,backup/filename)
draftpath=ROOT/'Config/modules-draft.json';draft=json.loads(draftpath.read_text('utf8'))
for module in draft['modules']:
    rid=module['id'];room=next(r for r in CFG['rooms'] if r['id']==rid)
    remove_meshes={'SM_Staff_PersonalBox'}
    if rid=='StaffRecreation':remove_meshes.update(('SM_Staff_Refrigerator','SM_Staff_KitchenCounter'))
    module['parts']=[p for p in module['parts'] if p.get('mesh','').rsplit('/',1)[-1] not in remove_meshes]
    patchkeys={'WaterDispenser','LaundryBasket'}
    if rid=='StaffRecreation':patchkeys.update(('KitchenCounterTop','TableTennisPaddle','CoffeeMachine','ElectricKettle','BathroomShell','Toilet'))
    for p in room['furniture']:
        if p['prototype'] not in patchkeys and p['id'] not in ('BathroomSink','BathroomMirror','BathroomLamp'):continue
        mesh,collision=shared(p['prototype'])
        old=next((q for q in module['parts'] if q.get('id')==p['id']),None)
        if old is None:old=dict(id=p['id']);module['parts'].append(old)
        old.update(mesh=mesh.get_path_name().split('.')[0],position=[p['position'][0]*100,-p['position'][1]*100,p['position'][2]*100],
            yaw=-p['yaw_blender_deg'],collision=collision,materials=[])
    if rid=='StaffChangingShowers':
        for c in module.get('scene_containers',[]):c.update(initial_random_open=True,random_open_tag='ColdSteel.SceneContainer.RandomOpen')
    if rid=='StaffRecreation':
        # Recover the receipt overrides when resuming after maps have already saved.
        all_overrides=dict(felt_overrides)
        for mapinfo in report['maps'].values():all_overrides.update(mapinfo.get('baize_overrides',{}))
        for p in module['parts']:
            if p.get('mesh') in all_overrides:p['materials']=all_overrides[p['mesh']]
        for spec in MAN['containers']:
            module.setdefault('scene_containers',[])
            module['scene_containers']=[c for c in module['scene_containers'] if c['container_id']!=spec['container_id']]
            module['scene_containers'].append(dict(actor_class='/Script/FPSGAME.ColdSteelSceneContainer',container_id=spec['container_id'],
                caption=spec['caption'],body=spec['body'],door=spec['door'],hinge=spec['hinge_cm'],opened_yaw=100,
                opening_motion='Swing',storage_pages=1,position=[spec['position'][0]*100,-spec['position'][1]*100,spec['position'][2]*100],
                yaw=-spec['yaw_blender_deg'],initial_random_open=spec['random_open'],random_open_tag='ColdSteel.SceneContainer.RandomOpen' if spec['random_open'] else ''))
        module['recreation_chair_layout_variants']=MAN['chair_layout']
        module['recreation_chair_layout_actor_class']='/Script/FPSGAME.StaffDormitoryLayout'
        module['variable_static_furniture']=[dict(mesh=CFG['ue_base']+'/Meshes/SM_Staff_Chair',layout_slot=p['id'],position=p['position_cm'],yaw=p['yaw_ue']) for p in MAN['chair_poses']]
        module['parts']=[p for p in module['parts'] if not p.get('mesh','').endswith('/SM_Staff_Chair')]
        # Variable chairs are represented above, never duplicated in the static part list.
        module.setdefault('lights',[])
        module['lights']=[p for p in module['lights'] if p.get('id')!='Bathroom']
        module['lights'].append(dict(id='Bathroom',position=[1220,-613,261],lumens=380,radius_cm=330,cast_shadows=False,
            max_draw_distance_cm=1400,fade_range_cm=300,indirect=.10,tint=[.79,.87,.82],role='Fill'))
draft['room_details_revision']=5
draftpath.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',unique_containers=67,authored_source=CFG['current_authored_source'],open_command='open '+CFG['sample_map']);record()
u.log('STAFF_ROOM_DETAILS_V5_DELIVERY_SAVED')
