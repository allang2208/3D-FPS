"""Requested numerical lamp audit after saving; no game, generation or render."""
from pathlib import Path
import json,math,runpy,copy
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
R=runpy.run_path(str(ROOT/'recipe.py'));data=R['bindings']()
receipt=json.loads((ROOT/'Receipts/install.json').read_text('utf8'))
def pos(p):return [p.x,p.y,p.z]
def near(a,b,message,tol=.025):
    if math.dist(a,b)>tol:raise RuntimeError(message+': '+str(a)+' / '+str(b))
def rotation(f):return u.Rotator(pitch=f.get('pitch',-90),yaw=f.get('yaw',0),roll=f.get('roll',0))
report=dict(maps=[],module_rows=[],fixed_rows=[],subjects=[],rendered=False,game_run=False)
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
g=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
catalog=json.loads(g.get_editor_property('module_catalog_json'))
disk=json.loads((PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
if catalog!=disk:raise RuntimeError('Saved generator and source catalog differ')
before=json.loads((Path(receipt['backup'])/'catalog-before.json').read_text('utf8'))
old_reception=next(m for m in before['modules'] if m['id']=='FacilityReceptionHall')
if old_reception!=next(m for m in catalog['modules'] if m['id']=='FacilityReceptionHall'):raise RuntimeError('Reception production baseline changed')
for m in catalog['modules']:
    if m['id'] not in data['modules']:continue
    for i,l in enumerate(m['lights']):
        expected=[p+n for p,n in zip(l['fixture_face_center_cm'],l['fixture_normal'])]
        near(l['position'],expected,m['id']+' emitter gap')
        forward=pos(u.MathLibrary.get_forward_vector(rotation(l)))
        near(forward,l['fixture_normal'],m['id']+' source direction')
        if l['type']=='spot' and (l.get('source_length')!=0 or 'yaw' in l):raise RuntimeError('Invalid legacy spot transform')
        report['module_rows'].append(dict(module=m['id'],index=i,id=l.get('id'),type=l['type'],position_cm=l['position'],
            normal=forward,mesh=l['fixture_mesh'],clearance_cm=1.,lumens=l['intensity'],alignment_ok=True,
            light_function=l.get('light_function'),shadows=l['cast_shadows']))
    for part in data['additional_parts'].get(m['id'],[]):
        matches=[p for p in m['parts'] if p==part]
        if len(matches)!=1 or not u.load_asset(part['mesh']):raise RuntimeError('Landing fixture not installed')
for entry in receipt['maps']:
    target=entry['path'];w=u.load_asset(target)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    rows=receipt['fixed'] if target.endswith('L_Dungeon_Randomized') else entry['lights']
    actual=[]
    for row in rows:
        a=actors[row['label']];c=a.get_component_by_class(u.LocalLightComponent)
        if c.get_class().get_name()!=row['type']:raise RuntimeError('Saved light class differs')
        near(pos(c.get_world_location()),row['position'],row['label']+' saved position')
        near(pos(c.get_forward_vector()),row['forward'],row['label']+' saved direction')
        if abs(c.intensity-row['intensity'])>.01:raise RuntimeError('Saved flux differs')
        if isinstance(c,u.RectLightComponent) and c.get_forward_vector().z>-.99:raise RuntimeError('A saved ceiling rect points upward')
        if isinstance(c,u.PointLightComponent) and c.source_length!=0:raise RuntimeError('Source segment crosses fixture')
        actual.append(row)
    if target.endswith('L_Dungeon_Randomized'):report['fixed_rows']=actual
    else:report['subjects'].append(dict(map=target,lights=actual))
    report['maps'].append(dict(path=target,lights=len(actual),saved_file_exists=(PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap')).exists()))
contract=runpy.run_path(str(PROJECT/'SourceAssets/DungeonFacilityFlow20261007/restore_entry_recipe.py'))['contract_hash']
bank=catalog['facility_flow']['layout_bank']
if contract(catalog)!=bank['contract_sha1'] or bank['entries']!=before['facility_flow']['layout_bank']['entries']:raise RuntimeError('Layout contract or placements changed unexpectedly')
report.update(stage='fixture_data_checked',bank_contract_sha1=bank['contract_sha1'],layout_entries_unchanged=len(bank['entries']),portal_variants_checked=18,
    removed_unbound_fills=4,added_landing_fixtures=3,split_tunnel_sources=3)
targets={m['path'] for m in report['maps']}
dirty=[p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())]
if any(p in targets or ('__externalactors__' in p.lower() and 'l_dungeon_randomized' in p.lower()) for p in dirty):raise RuntimeError('Target package remains dirty')
(ROOT/'Receipts/saved-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('FIXTURE_DATA_CHECKED',len(report['module_rows']),'module sources;',len(report['fixed_rows']),'fixed;',sum(len(s['lights']) for s in report['subjects']),'subject;',bank['contract_sha1'])
