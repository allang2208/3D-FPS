"""Local finish overlay for the second concourse; preserve established lighting."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/TransitFinish20261010'
REVISION='transit_connections_arrival_20261010';MODULE='FacilityTransit'
SUPERSEDED_FRAME=BASE+'/Meshes/SM_TransitFinish_ArrivalFrame'
SUBJECTS=('/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')
def manifest():return json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
def added(row):return row.get('transit_finish_revision')==REVISION
def lamps():
    rows=[]
    for name,x,yaw,lm,radius in (('GalleryGap',-2000,0,260,650),('Arrival',-2300,90,280,520)):
        rows.append(dict(id='TransitFinish_'+name,type='rect',position=[x,0,367.9],pitch=-90,yaw=yaw,roll=90,
            intensity=lm,radius=radius,optimized_radius_cm=radius,color=[.91,.82,.64],cast_shadows=True,
            source_width_cm=122.,source_height_cm=24.,indirect_lighting_intensity=.32,volumetric_scattering_intensity=0.,
            max_draw_distance_cm=3200,fade_range_cm=650,role='local',fixture_normal=[0,0,-1],
            fixture_face_center_cm=[x,0,368.9],fixture_mesh=BASE+'/Meshes/SM_TransitFinish_FixtureDiffusers',transit_finish_revision=REVISION))
    return rows
def relocate(part):
    key=part.get('fixture_id','');kind=part['mesh'].rsplit('_',1)[-1]
    if key==MODULE+'.vent.03':
        if kind=='VentBody':part['position']=[1450.,-1708.,540.]
        elif kind=='VentLeaf':part['position']=[1372.,-1708.,364.]
    elif key==MODULE+'.hatch.02':
        if kind=='HatchBody':part['position']=[2290.,-650.,0.]
        elif kind=='HatchLeaf':part['position']=[2290.,-723.,3.]
    elif key in (MODULE+'.service.00',MODULE+'.service.01'):
        part['position'][1]=1802. if kind=='DoorBody' else 1652.
def apply_module(module):
    if module['id']!=MODULE:return
    module['lights']=[p for p in module['lights'] if not added(p)]+lamps()
    module['parts']=[p for p in module['parts'] if not added(p)]
    for part in module['parts']:relocate(part)
    for item in manifest():
        module['parts'].append(dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],materials=[],fluid=False,
            collision=item['collision'],cast_shadow=item['cast_shadow'],transit_finish_revision=REVISION))
    assets={m['mesh'] for m in manifest()}|{v for m in manifest() for v in m['materials'].values()}
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-{SUPERSEDED_FRAME})|assets)
    module['transit_finish_revision']=REVISION
def installed():
    path=ROOT/'Receipts/install.json'
    return path.exists() and json.loads(path.read_text('utf8')).get('stage')=='maps_saved'
def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    out=copy.deepcopy(catalog);apply_module(next(m for m in out['modules'] if m['id']==MODULE))
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out)
    return out
def apply_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return {}
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_editor_world()!=world:raise RuntimeError('Expected the target editor world')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    offset=[5900,0,0];changed=[];has_vent=False
    # Old walkthroughs predate the production static fixtures. Only relocate
    # matching parts that are actually present; do not add orphan ductwork.
    for actor in actors.values():
        for sc in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=sc.static_mesh
            if not mesh:continue
            kind=mesh.get_name().removeprefix('SM_Entry_')
            if kind not in ('VentBody','VentLeaf','HatchBody','HatchLeaf','DoorBody','DoorLeaf','DoorLeafRight'):continue
            p=sc.get_world_location();x=p.x-offset[0];y=p.y;key=None
            if kind.startswith('Vent') and any(abs(x-v)<1 for v in (550,472,1450,1372)):key=MODULE+'.vent.03';has_vent=True
            elif kind.startswith('Hatch') and any(abs(x-v)<1 for v in (2350,2290)):key=MODULE+'.hatch.02'
            elif kind.startswith('Door') and abs(y-1720)<100:
                if abs(x+2090)<120:key=MODULE+'.service.00'
                elif abs(x-1390)<120:key=MODULE+'.service.01'
            if not key:continue
            row=dict(fixture_id=key,mesh=mesh.get_path_name().split('.')[0],position=[x,y,p.z]);relocate(row)
            sc.modify();old=sc.mobility;sc.set_mobility(u.ComponentMobility.MOVABLE)
            sc.set_world_location(u.Vector(row['position'][0]+5900,row['position'][1],row['position'][2]),False,True);sc.set_mobility(old)
            actor.modify();changed.append(key+'/'+kind)
    for item in manifest():
        if item['kind'].startswith('Vent') and not has_vent:continue
        label='FacilityTransit_Finish_'+item['kind'];actor=actors.get(label)
        if actor and REVISION not in [str(t) for t in actor.tags]:raise RuntimeError('Unowned actor '+label)
        if not actor:
            actor=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*offset),u.Rotator());actor.set_actor_label(label)
        actor.modify();sc=actor.static_mesh_component;sc.modify();sc.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_location_and_rotation(u.Vector(*offset),u.Rotator(),False,True)
        sc.set_static_mesh(u.load_asset(item['mesh']));sc.set_cast_shadow(item['cast_shadow']);sc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        sc.set_editor_property('generate_overlap_events',False);sc.set_mobility(u.ComponentMobility.STATIC)
        actor.set_folder_path('FacilityTransit/Finish');actor.set_editor_property('tags',['FacilityTransit.Subject',REVISION]);changed.append(label)
    for row in lamps():
        label='FacilityTransit_'+row['id'];actor=actors.get(label)
        if actor and REVISION not in [str(t) for t in actor.tags]:raise RuntimeError('Unowned actor '+label)
        loc=u.Vector(row['position'][0]+5900,0,row['position'][2]);rot=u.Rotator(pitch=-90,yaw=row['yaw'],roll=90)
        if not actor:actor=aa.spawn_actor_from_class(u.RectLight,loc,rot);actor.set_actor_label(label)
        actor.modify();light=actor.get_component_by_class(u.RectLightComponent);light.modify();light.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_location_and_rotation(loc,rot,False,True);light.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        light.set_intensity(row['intensity']);light.set_attenuation_radius(row['radius']);light.set_cast_shadows(True);light.set_light_color(u.LinearColor(*row['color'],1))
        for key,val in dict(source_width=122.,source_height=24.,indirect_lighting_intensity=.32,volumetric_scattering_intensity=0.,max_draw_distance=3200.,max_distance_fade_range=650.).items():light.set_editor_property(key,val)
        actor.set_folder_path('FacilityTransit/Finish');actor.set_editor_property('tags',['FacilityTransit.Subject',REVISION]);changed.append(label)
    return dict(changed=changed,production_vent_present=has_vent)
