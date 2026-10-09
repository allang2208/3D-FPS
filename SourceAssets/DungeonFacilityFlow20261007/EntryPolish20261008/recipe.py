"""Idempotent local appearance update; all sockets and placement cells stay intact."""
from pathlib import Path
import json, copy

ROOT=Path(__file__).resolve().parent
REVISION='entry_local_lights_and_detail_20261008'
BASE='/Game/Dungeons/FacilityFlow20261007/EntryPolish20261008'

def apply_modules(reception,entry):
    manifest=json.loads((ROOT/'geometry.json').read_text('utf8'))
    for m in (reception,entry):
        m['parts']=[p for p in m['parts'] if not p['mesh'].startswith(BASE+'/')]
        m['runtime_assets']=[p for p in m.get('runtime_assets',[]) if not p.startswith(BASE+'/')]
    reception['parts']=[p for p in reception['parts'] if not p['mesh'].split('.')[0].endswith('/SM_FacilityFlow_BreachThreshold')]
    for item in manifest['meshes']:
        target=entry if item['kind'].startswith('Passage') else reception
        target['parts'].append(dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],
            collision=False,cast_shadow=item['cast_shadow'],fluid=False,materials=[]))
        target['runtime_assets']=sorted(set(target.get('runtime_assets',[]))|{item['mesh']}|set(item['materials'].values()))
    entry['lights']=[l for l in entry['lights'] if l.get('detail_revision')!=REVISION]
    for light in entry['lights']:
        if light.get('type','point')=='point' and light['position'] in ([0,-200,248],[0,-600,248]):
            light['intensity']=300
    for name,pos,power,radius,color in (
        ('Breach_Left',[-182,-1090,304],750,620,[1,.85,.68]),
        ('Breach_Right',[182,-1090,304],750,620,[1,.85,.68]),
        ('Ceiling_Transition',[0,-835,245],450,460,[.82,.91,.85]),
    ):
        entry['lights'].append(dict(id='EntryPolish_'+name,detail_revision=REVISION,
            position=pos,type='point',intensity=power,radius=radius,optimized_radius_cm=radius,
            color=color,cast_shadows=False,role='entry',max_draw_distance_cm=2200,
            fade_range_cm=450,indirect_lighting_intensity=.18))
    entry['detail_revision']=REVISION
    reception['entry_detail_revision']=REVISION

def extend(catalog,contract_hash):
    bank=catalog['facility_flow']['layout_bank']
    old_hash=contract_hash(catalog)
    if old_hash!=bank['contract_sha1']:
        raise RuntimeError('Preserve unrelated/stale layout bank before entry appearance update')
    result=copy.deepcopy(catalog)
    flow=result['facility_flow']
    reception=next(m for m in result['modules'] if m['id']==flow['reception'])
    entry=next(m for m in result['modules'] if m['id']==flow['entrance'])
    apply_modules(reception,entry)
    bank=result['facility_flow']['layout_bank']
    bank['contract_sha1']=contract_hash(result)
    bank['entry_detail_update']=dict(revision=REVISION,source_contract_sha1=old_hash,
        placement_data_changed=False,sockets_changed=False,regression_run=False)
    return result
