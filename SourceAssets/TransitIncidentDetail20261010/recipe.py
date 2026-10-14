"""Replace only owned incident prop geometry; keep the saved room's transforms and lighting."""
from pathlib import Path
import json,copy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/TransitIncidentDetail20261010';OLD='/Game/Dungeons/TransitIncidentDressing20261010'
REVISION='transit_incident_detail_20261010';MODULE='FacilityTransit'
SUBJECTS=('/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')

def manifest():return json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
def replacements():return {OLD+'/Meshes/SM_Incident_'+r['kind']:r['mesh'] for r in manifest()}
def old_materials():
    return {v for m in json.loads((ROOT.parent/'TransitIncidentDressing20261010/geometry.json').read_text('utf8'))['meshes'] for v in m['materials'].values() if v.startswith(OLD+'/')}

def apply_module(module):
    if module['id']!=MODULE:return []
    table=replacements();changes=[]
    for row in module['parts']:
        if row.get('incident_revision')!='transit_incident_20261010':continue
        if row['mesh'] in table:
            before=row['mesh'];row['mesh']=table[before];changes.append(dict(id=row.get('id'),before=before,after=row['mesh']))
        if row['mesh'] in table.values():row['incident_detail_revision']=REVISION
    superseded=set(table)|old_materials()
    used={p['mesh'] for p in module['parts']}|{m for p in module['parts'] for m in p.get('materials',[])}
    assets={p['mesh'] for p in module['parts'] if p.get('incident_detail_revision')==REVISION}|{v for m in manifest() for v in m['materials'].values()}
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-(superseded-used))|assets)
    module['incident_detail_revision']=REVISION
    return changes

def installed():
    p=ROOT/'Receipts/install.json'
    return p.exists() and json.loads(p.read_text('utf8')).get('stage')=='maps_saved'

def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    result=copy.deepcopy(catalog);apply_module(next(m for m in result['modules'] if m['id']==MODULE))
    result['facility_flow']['layout_bank']['contract_sha1']=contract_hash(result);return result

def apply_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return []
    table=replacements();changed=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if 'transit_incident_20261010' not in [str(t) for t in actor.tags]:continue
        for sc in actor.get_components_by_class(u.StaticMeshComponent):
            if not sc.static_mesh:continue
            path=sc.static_mesh.get_path_name().split('.')[0]
            if path not in table:continue
            actor.modify();sc.modify();mobility=sc.mobility;sc.set_mobility(u.ComponentMobility.MOVABLE)
            sc.set_static_mesh(u.load_asset(table[path]));sc.set_mobility(mobility)
            actor.set_editor_property('tags',list(actor.tags)+([] if REVISION in [str(t) for t in actor.tags] else [REVISION]))
            changed.append(actor.get_actor_label())
    return changed
