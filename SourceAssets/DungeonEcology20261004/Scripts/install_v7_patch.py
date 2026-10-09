"""Import the three revised meshes and patch only the requested scene actors."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=ROOT/'Scripts/install.py'
# Retain the production import/material/collision recipe without regenerating maps.
exec(compile(script.read_text('utf8').split('# Drafts are source-only')[0],str(script),'exec'),globals())
previous=json.loads((ROOT/'Revisions/v6/Receipts/install-v6.json').read_text('utf8'))
for key,value in previous['maps'].items():report['maps'].setdefault(key,value)
changed={item['name']:(mesh,item) for mesh,item in meshitems.values() if not item.get('reused')}
b=CFG['rooms'][2]
place_wall_groups(b)
for p in b['parts']:
    p['position']=wall_position(asset(p['mesh']),p['position'],p['yaw'],p.get('wall_mount'))
for c in b['containers']:
    if not c['container_id'].startswith(('EcoBiosphere.PPE','EcoBiosphere.Records')):continue
    reference=BASE+'/Meshes/SM_Eco_RecordsCarcass' if c['body'].endswith('RecordsFrame') else c['body']
    c['position_m']=wall_position(asset(reference),c['position_m'],c['yaw_blender'],c.get('wall_mount'))

def relocate(actor,p,yaw,off):
    actor.modify()
    actor.set_actor_location(pos(p,off),False,True)
    actor.set_actor_rotation(u.Rotator(pitch=0,yaw=-yaw,roll=0),True)

targets=[(CFG['rooms'][0]['map'],False),(b['map'],False),(CFG['sample_map'],True)]
for target,combined in targets:
    old=report['maps'].get(target,{})
    if old.get('stage')=='map_saved' and old.get('geometry_revision',0)>=8:continue
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load '+target)
    actors={a.get_actor_label():a for a in AA.get_all_level_actors() if 'Ecology.Subject' in [str(t) for t in a.tags]}
    edited=[]
    for name,(mesh,item) in changed.items():
        if not combined and (target==b['map'])!=(item['room_id']=='EcoBiosphere'):continue
        label='EcoSubject_'+name
        actor=actors.get(label)
        if not actor:raise RuntimeError('Missing authored mesh actor '+label+' in '+target)
        actor.modify();actor.static_mesh_component.modify();actor.static_mesh_component.set_static_mesh(mesh)
        edited.append(label)
    if combined or target==b['map']:
        off=b['offset'] if combined else [0,0,0]
        for index,p in enumerate(b['parts']):
            label='EcoSubject_EcoBiosphere_Fixed'+str(index)
            actor=actors.get(label)
            if not actor:raise RuntimeError('Missing office part '+label)
            relocate(actor,p['position'],p['yaw'],off);edited.append(label)
        for c in b['containers']:
            if not c['container_id'].startswith(('EcoBiosphere.PPE','EcoBiosphere.Records')):continue
            label='EcoSubject_'+c['container_id'];actor=actors.get(label)
            if not actor:raise RuntimeError('Missing office container '+label)
            relocate(actor,c['position_m'],c['yaw_blender'],off);edited.append(label)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(old,stage='map_saved',geometry_revision=8,updated_actors=edited,patch_only=True)
    record();u.log('ECOLOGY_V7_MAP_PATCH_SAVED '+target)

draft_path=ROOT/'Config/modules-draft.json';draft=json.loads(draft_path.read_text('utf8'))
for module in draft['modules']:
    room=next(r for r in CFG['rooms'] if r['id']==module['id'])
    for part in module['parts']:
        name=part['mesh'].rsplit('/',1)[-1]
        if name in changed:part['mesh']=changed[name][1]['asset']
    if module['id']=='EcoBiosphere':
        module['author_fixed_parts']=room['parts'];module['author_containers']=room['containers']
        module['author_furniture_keepout_m']=room['furniture_keepout_m']
draft_path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',saved_revision=CFG['revision'],new_meshes=len(changed),
    patched_maps=[t[0] for t in targets],retained_map=CFG['rooms'][1]['map'],
    container_physical_groups=24,unique_search_entries=32,game_run=False,tests_run=False,rendered=False)
record();u.log('ECOLOGY_V7_LOCAL_REVISION_SAVED')
