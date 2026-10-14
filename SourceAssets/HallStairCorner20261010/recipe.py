"""Persist the two stair repairs and local corner illumination across room rebuilds."""
from pathlib import Path
import json,copy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/HallStairCorner20261010';REVISION='hall_stair_corner_20261010'
MODULES={'FacilityReceptionHall':'Reception','FacilityTransit':'Transit'}
SUBJECTS=('/Game/GameMaps/Design/L_ReceptionHall_Subject','/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')
def manifest():return json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
def replacements():return {i['old']:i['mesh'] for i in manifest() if i['old']}
def lamps():
    rows=[]
    for side in (-1,1):
        for key,x,z,floor,lm,radius,width,depth in (
            ('WestGround',-2240,367,0,380,760,94,26),
            ('WestGallery',-2240,765,420,280,700,94,26),
            ('EastGround',2353,347,0,360,780,32,94)):
            rows.append(dict(id='CornerMinimum_'+key+('_N' if side>0 else '_S'),type='rect',position=[x,side*1560,z],
                pitch=-90,yaw=0,roll=90,intensity=lm,radius=radius,optimized_radius_cm=radius,color=[.90,.82,.65],
                cast_shadows=True,source_width_cm=width,source_height_cm=depth,indirect_lighting_intensity=.25,
                volumetric_scattering_intensity=0.,max_draw_distance_cm=6500,fade_range_cm=700,role='local',
                fixture_normal=[0,0,-1],fixture_face_center_cm=[x,side*1560,z+1],
                fixture_mesh=BASE+'/Meshes/SM_HSC_Transit_CornerDiffusers',corner_floor_z_cm=floor,
                minimum_illumination_steady=True,hall_stair_corner_revision=REVISION))
    return rows
def added(row):return row.get('hall_stair_corner_revision')==REVISION
def apply_module(module):
    room=MODULES.get(module['id'])
    if not room:return []
    items=[i for i in manifest() if i['room']==room];table={i['old']:i['mesh'] for i in items if i['old']};changes=[]
    for p in module['parts']:
        if p['mesh'] in table:
            before=p['mesh'];p['mesh']=table[before];changes.append(dict(before=before,after=p['mesh']))
        if p['mesh'] in table.values():p['hall_stair_corner_revision']=REVISION
    if room=='Transit':
        fixture_paths={i['mesh'] for i in items if not i['old']}
        module['parts']=[p for p in module['parts'] if p['mesh'] not in fixture_paths]
        for i in items:
            if not i['old']:module['parts'].append(dict(mesh=i['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],materials=[],
                fluid=False,collision=False,cast_shadow=i['cast_shadow'],hall_stair_corner_revision=REVISION))
        module['lights']=[p for p in module['lights'] if not added(p)]+lamps()
    assets={i['mesh'] for i in items}|{v for i in items for v in i['materials'].values()}
    used={p['mesh'] for p in module['parts']}
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-(set(table)-used))|assets)
    module['hall_stair_corner_revision']=REVISION
    return changes
def installed():
    p=ROOT/'Receipts/install.json'
    return p.exists() and json.loads(p.read_text('utf8')).get('stage')=='maps_saved'
def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    out=copy.deepcopy(catalog)
    for m in out['modules']:apply_module(m)
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out);return out
def apply_subject(world):
    import unreal as u
    target=world.get_path_name().split('.')[0]
    if target not in SUBJECTS:return {}
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    table=replacements();changed=[]
    for a in actors.values():
        for sc in a.get_components_by_class(u.StaticMeshComponent):
            if not sc.static_mesh:continue
            path=sc.static_mesh.get_path_name().split('.')[0]
            if path not in table:continue
            a.modify();sc.modify();mobility=sc.mobility;sc.set_mobility(u.ComponentMobility.MOVABLE)
            sc.set_static_mesh(u.load_asset(table[path]));sc.set_mobility(mobility)
            a.set_editor_property('tags',list(a.tags)+([] if REVISION in [str(t) for t in a.tags] else [REVISION]))
            changed.append(a.get_actor_label())
    if target==SUBJECTS[0]:return dict(meshes=changed,lights=[])
    for item in manifest():
        if item['old']:continue
        label='FacilityTransit_'+item['kind'];a=actors.get(label)
        if a and REVISION not in [str(t) for t in a.tags]:raise RuntimeError('Unowned actor '+label)
        if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(5900,0,0),u.Rotator());a.set_actor_label(label)
        a.modify();sc=a.static_mesh_component;sc.modify();sc.set_mobility(u.ComponentMobility.MOVABLE)
        a.set_actor_location_and_rotation(u.Vector(5900,0,0),u.Rotator(),False,True)
        sc.set_static_mesh(u.load_asset(item['mesh']));sc.set_cast_shadow(item['cast_shadow']);sc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        sc.set_editor_property('generate_overlap_events',False);sc.set_mobility(u.ComponentMobility.STATIC)
        a.set_folder_path('FacilityTransit/CornerLights');a.set_editor_property('tags',['FacilityTransit.Subject',REVISION]);changed.append(label)
    light_names=[]
    for row in lamps():
        label='FacilityTransit_'+row['id'];a=actors.get(label)
        if a and REVISION not in [str(t) for t in a.tags]:raise RuntimeError('Unowned actor '+label)
        loc=u.Vector(row['position'][0]+5900,row['position'][1],row['position'][2]);rot=u.Rotator(pitch=-90,yaw=0,roll=90)
        if not a:a=aa.spawn_actor_from_class(u.RectLight,loc,rot);a.set_actor_label(label)
        a.modify();c=a.get_component_by_class(u.RectLightComponent);c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
        a.set_actor_location_and_rotation(loc,rot,False,True);c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        c.set_intensity(row['intensity']);c.set_attenuation_radius(row['radius']);c.set_cast_shadows(True);c.set_light_color(u.LinearColor(*row['color'],1))
        for key,value in dict(source_width=row['source_width_cm'],source_height=row['source_height_cm'],indirect_lighting_intensity=.25,
            volumetric_scattering_intensity=0.,max_draw_distance=6500.,max_distance_fade_range=700.).items():c.set_editor_property(key,value)
        a.set_folder_path('FacilityTransit/CornerLights');a.set_editor_property('tags',['FacilityTransit.Subject',REVISION]);light_names.append(label)
    return dict(meshes=changed,lights=light_names)
