"""Reapply the saved entrance, portal fittings and maintenance layout after rebuilds."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/FacilityDetailRepair20261010';REVISION='facility_detail_repair_20261010'
GLASS=BASE+'/FX/NS_GlassShatter_NoMarks'
OLD_GLASS='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass'
SUBJECTS=('/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')
TOOL_X={'Tool0':-380,'Tool1':-5}
# Keep the complete maintenance assembly east of the stair foot at X=-500 cm.
# Meshes retain their authored pivots; only their placement moves by two metres.
MAINTENANCE_SHIFT_CM=200
MAINTENANCE_TAG='transit_maintenance_clearance_20261013'
MAINTENANCE_MESHES={BASE+'/Meshes/SM_FDR_Hall_'+kind for kind in ('ServiceBench','MaintenancePanel','DetailPlates')}

def place_maintenance(module):
    changed=[]
    for part in module['parts']:
        if part['mesh'] not in MAINTENANCE_MESHES:continue
        position=list(part.get('position',[0,0,0]))
        position[0]+=MAINTENANCE_SHIFT_CM-part.get('maintenance_shift_cm',0)
        part['position']=position;part['maintenance_shift_cm']=MAINTENANCE_SHIFT_CM
        changed.append(dict(mesh=part['mesh'],position=position))
    for actor in module.get('runtime_actors',[]):
        cid=actor.get('container_id','')
        if cid in ('FacilityTransit.Tool0','FacilityTransit.Tool1'):
            actor['position']=[TOOL_X[cid.split('.')[-1]],1720,85]
            changed.append(dict(container_id=cid,position=actor['position']))
    return changed

def place_maintenance_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return []
    changed=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        cid=str(actor.get_editor_property('container_id')) if isinstance(actor,u.ColdSteelSceneContainer) else ''
        target=None
        if cid in ('FacilityTransit20261007.Tool0','FacilityTransit20261007.Tool1'):
            target=u.Vector(5900+TOOL_X[cid.split('.')[-1]],1720,85)
        elif isinstance(actor,u.StaticMeshActor):
            mesh=actor.static_mesh_component.static_mesh
            if not mesh or mesh.get_path_name().split('.')[0] not in MAINTENANCE_MESHES:continue
            if MAINTENANCE_TAG in [str(t) for t in actor.tags]:continue
            target=actor.get_actor_transform().transform_location(u.Vector(MAINTENANCE_SHIFT_CM,0,0))
        if target is None:continue
        actor.modify();actor.set_actor_location(target,False,True)
        if MAINTENANCE_TAG not in [str(t) for t in actor.tags]:actor.set_editor_property('tags',list(actor.tags)+[MAINTENANCE_TAG])
        changed.append(dict(actor=actor.get_actor_label(),position=[target.x,target.y,target.z]))
    return changed
def patch_glass(value):
    count=0
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='impact_particles' and item==OLD_GLASS:value[key]=GLASS;count+=1
            else:count+=patch_glass(item)
    elif isinstance(value,list):
        for item in value:count+=patch_glass(item)
    return count
def data():return json.loads((ROOT/'geometry.json').read_text('utf-8-sig'))
def manifest():return data()['meshes']
def replacements():return {m['old']:m['mesh'] for m in manifest() if m['old']}
def superseded():return set(replacements())|set(data()['remove'])
def patch_parts(parts):
    items=manifest();table=replacements();remove=set(data()['remove']);out=[];changes=[];poses={}
    for p in parts:
        mesh=p['mesh'];item=next((i for i in items if mesh in (i['old'],i['mesh'])),None)
        # Shifted maintenance pieces are children of the hall assembly, not
        # additional hall roots from which to duplicate the shared label mesh.
        if item and item['mesh'] not in MAINTENANCE_MESHES:
            key=(item['room'],tuple(p.get('position',[0,0,0])),p.get('yaw',0),tuple(p.get('scale',[1,1,1])))
            poses.setdefault(key,copy.deepcopy(p))
        if mesh in remove:changes.append(dict(removed=mesh));continue
        q=copy.deepcopy(p)
        if mesh in table:q['mesh']=table[mesh];changes.append(dict(before=mesh,after=q['mesh']))
        if item:q['facility_detail_revision']=REVISION
        if not (item and item['old'] is None):out.append(q)
    for (room,*_),prototype in poses.items():
        for item in items:
            if item['room']!=room or item['old']:continue
            q={k:copy.deepcopy(prototype[k]) for k in ('position','yaw','pitch','roll','scale') if k in prototype}
            q.update(mesh=item['mesh'],materials=[],collision=item['collision'],cast_shadow=item['cast_shadow'],fluid=False,facility_detail_revision=REVISION)
            out.append(q)
    return out,changes
def apply_catalog(catalog):
    changes={};module=next(m for m in catalog['modules'] if m['id']=='FacilityTransit')
    module['parts'],changes['default_parts']=patch_parts(module['parts'])
    for route,variants in catalog['facility_flow']['route_portal_variants'].items():
        for theme,parts in variants.items():
            variants[theme],changed=patch_parts(parts)
            if changed:changes[route+'.'+theme]=changed
    for a in module.get('runtime_actors',[]):
        if a.get('container_id') in ('FacilityTransit.Tool0','FacilityTransit.Tool1'):
            a['position']=[TOOL_X[a['container_id'].split('.')[-1]],1720,85]
    assets={i['mesh'] for i in manifest()}|{v for i in manifest() for v in i['materials'].values()}|{GLASS}
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-superseded())|assets)
    module['facility_detail_revision']=REVISION
    changes['glass_definitions']=patch_glass(catalog)
    table=replacements()
    for m in catalog['modules']:
        if GLASS in json.dumps(m):m['runtime_assets']=sorted(set(m.get('runtime_assets',[]))|{GLASS})
        for light in m.get('lights',[]):
            if light.get('fixture_mesh') in table:light['fixture_mesh']=table[light['fixture_mesh']]
    changes['maintenance_placement']=place_maintenance(module)
    return changes
def installed():
    receipt=ROOT/'Receipts/install.json'
    return receipt.exists() and json.loads(receipt.read_text('utf-8-sig')).get('stage')=='maps_saved'
def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    out=copy.deepcopy(catalog);apply_catalog(out)
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out);return out
def apply_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return {}
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor));labels={a.get_actor_label():a for a in actors}
    table=replacements();remove=set(data()['remove']);items=manifest();changes=[];removed=[];poses={};tools=[];glass=[]
    for actor in actors:
        for pane in actor.get_components_by_class(u.WardBreakableGlass):
            particle=pane.get_editor_property('impact_particles')
            if not particle or particle.get_path_name().split('.')[0]==OLD_GLASS:
                actor.modify();pane.modify();pane.set_editor_property('impact_particles',u.load_asset(GLASS));glass.append(actor.get_actor_label())
        for sc in actor.get_components_by_class(u.StaticMeshComponent):
            if not sc.static_mesh:continue
            path=sc.static_mesh.get_path_name().split('.')[0]
            if path in remove:
                if not isinstance(actor,u.StaticMeshActor):raise RuntimeError('Expected standalone obsolete fitting: '+actor.get_actor_label())
                removed.append(actor.get_actor_label());aa.destroy_actor(actor);break
            item=next((i for i in items if path in (i['old'],i['mesh'])),None)
            if not item:continue
            transform=actor.get_actor_transform();pos=actor.get_actor_location();rot=actor.get_actor_rotation()
            key=(item['room'],round(pos.x,3),round(pos.y,3),round(pos.z,3),round(rot.yaw,3))
            if item['mesh'] not in MAINTENANCE_MESHES:
                poses.setdefault(key,(transform,actor.get_folder_path(),list(actor.tags)))
            if path in table:
                actor.modify();sc.modify();mobility=sc.mobility;sc.set_mobility(u.ComponentMobility.MOVABLE)
                sc.set_static_mesh(u.load_asset(table[path]));sc.set_mobility(mobility)
                actor.set_editor_property('tags',list(actor.tags)+([] if REVISION in [str(t) for t in actor.tags] else [REVISION]))
                changes.append(actor.get_actor_label())
        if isinstance(actor,u.ColdSteelSceneContainer):
            cid=str(actor.get_editor_property('container_id'))
            if cid in ('FacilityTransit20261007.Tool0','FacilityTransit20261007.Tool1'):
                x=TOOL_X[cid.split('.')[-1]];actor.modify();actor.set_actor_location(u.Vector(5900+x,1720,85),False,True);tools.append(cid)
    for (room,x,y,z,yaw),(transform,folder,tags) in poses.items():
        for item in items:
            if item['room']!=room or item['old']:continue
            label='FacilityDetail_'+room+'_'+item['kind']+'_'+str(int(x))+'_'+str(int(y))
            a=labels.get(label)
            if a and REVISION not in [str(t) for t in a.tags]:raise RuntimeError('Preserve unrelated actor '+label)
            if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,y,z),u.Rotator());a.set_actor_label(label)
            a.modify();sc=a.static_mesh_component;sc.modify();sc.set_mobility(u.ComponentMobility.MOVABLE)
            a.set_actor_transform(transform,False,True);sc.set_static_mesh(u.load_asset(item['mesh']))
            sc.set_cast_shadow(item['cast_shadow']);sc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            sc.set_editor_property('generate_overlap_events',False);sc.set_mobility(u.ComponentMobility.STATIC)
            a.set_folder_path(folder);a.set_editor_property('tags',tags+([] if REVISION in [str(t) for t in tags] else [REVISION]))
            changes.append(label)
    maintenance=place_maintenance_subject(world)
    return dict(meshes=changes,removed=removed,moved_toolboxes=tools,glass=glass,maintenance_placement=maintenance)
