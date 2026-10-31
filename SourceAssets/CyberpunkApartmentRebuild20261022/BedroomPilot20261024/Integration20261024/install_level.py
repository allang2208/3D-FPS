"""Install the approved bedroom into the current apartment without replacing its world."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,hashlib,copy,os,gc
R=Path(__file__).resolve().parent;ROOT=R.parent;PROJECT=R.parents[3]
MAP='/Game/GameMaps/L_CyberpunkApartment'
PILOT='/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024'
TAG='Apartment.Bed2.Refined20261024'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()

def read(p):return json.loads(p.read_text('utf8'))
def stamp():return datetime.now().astimezone().isoformat()
def vec(v):return list(v.to_tuple())
def pose(a):
    rot=a.get_actor_rotation()
    return dict(position=vec(a.get_actor_location()),rotation=dict(pitch=rot.pitch,yaw=rot.yaw,roll=rot.roll),scale=vec(a.get_actor_scale3d()))
def place(a,row):
    c=a.root_component;mobility=c.get_editor_property('mobility')
    c.set_mobility(u.ComponentMobility.MOVABLE)
    a.set_actor_location(u.Vector(*row['position']),False,False);a.set_actor_rotation(u.Rotator(**row['rotation']),False);a.set_actor_scale3d(u.Vector(*row['scale']))
    c.set_mobility(mobility)
def mark(a):
    a.modify();tags=[v for v in a.tags if not str(v).startswith('Cyberpunk.BedroomPilot')]
    if u.Name(TAG) not in tags:tags.append(u.Name(TAG))
    a.set_editor_property('tags',tags)

def capture_approved():
    destination=R/'approved-bedroom.json'
    if destination.exists():return read(destination)
    world=u.EditorLoadingAndSavingUtils.load_map(PILOT)
    if not world:raise RuntimeError('Approved bedroom source map unavailable')
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    installed=read(ROOT/'RefinementV3/installed.json');corrected=read(ROOT/'RefinementV2/installed.json')
    data=dict(source_map=PILOT,target_map=MAP,meshes=[],existing_layout=[],lights=[],captured_at=stamp())
    for entry in installed['actors']:
        a=actors[entry['actor']];c=a.static_mesh_component
        data['meshes'].append(dict(actor=entry['actor'],key=entry['key'],transform=pose(a),mesh=c.static_mesh.get_path_name(),materials=[m.get_path_name() if m else None for m in c.get_materials()],collision_profile=str(c.get_collision_profile_name()),collision_enabled=next(n for n in ['NO_COLLISION','QUERY_ONLY','PHYSICS_ONLY','QUERY_AND_PHYSICS','PROBE_ONLY','QUERY_AND_PROBE'] if hasattr(u.CollisionEnabled,n) and c.get_collision_enabled()==getattr(u.CollisionEnabled,n)),cast_shadow=c.get_editor_property('cast_shadow')))
    for entry in corrected['existing_layout_corrections']:
        a=actors[entry['actor']];parent=a.get_attach_parent_actor()
        data['existing_layout'].append(dict(actor=entry['actor'],transform=pose(a),parent=parent.get_actor_label() if parent else None))
    atmosphere=actors['AP7_Atmosphere']
    for word in ('Left','Right'):
        label='BP_ReadingLight_'+word;a=actors[label];c=a.get_component_by_class(u.SpotLightComponent)
        b=next(b for b in atmosphere.get_editor_property('lights') if b.actor and b.actor.get_actor_label()==label)
        props={key:c.get_editor_property(key) for key in ['intensity','temperature','use_temperature','attenuation_radius','inner_cone_angle','outer_cone_angle','cast_shadows','source_radius','max_draw_distance','max_distance_fade_range']}
        binding={key:b.get_editor_property(key) for key in ['base_intensity','day_factor','night_factor','room_index']}
        binding['fixtures']=[f.get_actor_label() for f in b.get_editor_property('fixtures')]
        data['lights'].append(dict(actor=label,transform=pose(a),properties=props,binding=binding))
    destination.write_text(json.dumps(data,indent=2),encoding='utf8')
    return data

def apply_upgrade(world):
    if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Formal apartment required')
    data=read(R/'approved-bedroom.json');assets=read(ROOT/'RefinementV3/assets_saved.json')
    design=runpy.run_path(str(ROOT/'RefinementV3/design.py'));surfaces=design['SURFACES'];base=design['BASE']
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    required=['AP_Bed2_Bed','AP7_Atmosphere']+[r['actor'] for r in data['existing_layout']]
    missing=[name for name in required if name not in actors]
    if missing:raise RuntimeError('Current apartment missing bedroom anchors: '+str(missing))
    report=dict(map=MAP,created=[],updated=[],layout=[],lights=[],game_run=False)
    for row in data['meshes']:
        label=row['actor'];a=actors.get(label)
        if not a:
            a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label);actors[label]=a;report['created'].append(label)
        else:report['updated'].append(label)
        mark(a);a.set_folder_path('Apartment20261022/Bed2/'+row['key'])
        c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.MOVABLE)
        mesh=u.load_asset(assets['meshes'][row['key']]['path'])
        if not mesh:raise RuntimeError('Missing saved bedroom mesh '+row['key'])
        c.set_static_mesh(mesh);c.set_editor_property('override_materials',[]);place(a,row['transform'])
        if row['key'] in ('BedRefined','FootThrow'):
            for i,slot in enumerate(mesh.static_materials):
                role=str(slot.material_slot_name);name='MI_BP3_'+row['key']+'_'+role;path=base+'/Materials/'+name
                # The approved instances are already compiled and calibrated.
                # Integration only references them; never resave loaded art packages.
                mat=u.load_asset(path)
                if not mat:raise RuntimeError('Missing approved surface instance '+path)
                c.set_material(i,mat)
        c.set_collision_profile_name(row['collision_profile']);c.set_collision_enabled(getattr(u.CollisionEnabled,row['collision_enabled']))
        a.set_actor_enable_collision(row['collision_enabled']!='NO_COLLISION');c.set_editor_property('cast_shadow',row['cast_shadow']);c.set_editor_property('visible_in_ray_tracing',True);c.set_mobility(u.ComponentMobility.STATIC)
    # Restore the approved furniture positions parent-first; keep all native actors,
    # container IDs, attachments, device links and interaction components.
    bylabel={row['actor']:row for row in data['existing_layout']}
    def depth(row,seen=None):
        seen=set() if seen is None else seen
        parent=row['parent']
        if parent not in bylabel or parent in seen:return 0
        return 1+depth(bylabel[parent],seen|{parent})
    for row in sorted(data['existing_layout'],key=depth):
        a=actors[row['actor']];a.modify();place(a,row['transform']);report['layout'].append(row['actor'])
    atmosphere=actors['AP7_Atmosphere'];atmosphere.modify()
    labels={row['actor'] for row in data['lights']}
    bindings=[b for b in atmosphere.get_editor_property('lights') if not (b.actor and b.actor.get_actor_label() in labels)]
    for row in data['lights']:
        a=actors.get(row['actor'])
        if not a:a=aa.spawn_actor_from_class(u.SpotLight,u.Vector());a.set_actor_label(row['actor']);actors[row['actor']]=a
        mark(a);a.set_folder_path('Apartment20261022/Bed2/Lighting')
        c=a.get_component_by_class(u.SpotLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE);place(a,row['transform'])
        c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        for key,value in row['properties'].items():c.set_editor_property(key,value)
        b=u.ApartmentLightBinding();b.set_editor_property('actor',a)
        for key,value in row['binding'].items():b.set_editor_property(key,[actors[n] for n in value] if key=='fixtures' else value)
        bindings.append(b);report['lights'].append(row['actor'])
    atmosphere.set_editor_property('lights',bindings)
    config=PROJECT/'Content/ColdSteelData/apartment_furniture_rest.json';raw=config.read_bytes();settings=json.loads(raw.decode('utf-8-sig'))
    bedpath=assets['meshes']['BedRefined']['path']
    if not any(r['mesh']==bedpath for r in settings['furniture']):
        original='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV14/Meshes/SM_AP14_Bed.SM_AP14_Bed'
        alias=copy.deepcopy(next(r for r in settings['furniture'] if r['mesh']==original));alias['mesh']=bedpath;settings['furniture'].append(alias)
        if config.read_bytes()!=raw:raise RuntimeError('Concurrent furniture configuration edit')
        temp=R/'rest-config.updated.json';temp.write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,config)
    report['bed_rest_mesh']=bedpath
    # Reuse the current approved bed on the other existing bedroom after any
    # upstream apartment/bedroom rebuild, without recreating a sample map.
    bed_reuse=ROOT.parent/'BedReuse20261025'
    if (bed_reuse/'installed.json').exists():
        report['bed_reuse']=runpy.run_path(str(bed_reuse/'install_level.py'))['apply_upgrade'](world)
    return report

def main():
    subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if subsystem and subsystem.get_game_world():raise RuntimeError('Wait for the current PIE session to finish')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    capture_approved()
    backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
    source=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(source,backup/source.name)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    report=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Formal apartment save failed')
    report.update(stage='formal_apartment_saved',saved_at=stamp(),backup=str(backup/source.name),map_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('BEDROOM_FORMAL_APARTMENT_SAVED',len(report['created']),len(report['updated']),len(report['layout']))
if __name__=='__main__':main()
