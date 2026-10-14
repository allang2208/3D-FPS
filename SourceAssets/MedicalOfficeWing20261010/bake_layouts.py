"""Author the replacement fallback placement bank; no assembly or gameplay.

This generates the production layout data required by the changed geometry and
seven-slot branches. It does not replay/test the resulting bank or run a game.
"""
import json,itertools,copy,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
if 'DungeonLayoutBake' not in u.SystemLibrary.get_command_line():raise RuntimeError('Offline layout bake flag required')
catalog=json.loads((ROOT/'Config/catalog-pending.json').read_text('utf8'))
themes=sorted(r['id'] for r in catalog['themed_routes']['routes'])
pairs=sorted({tuple(sorted((p[i],p[i+1]) for i in (0,2,4))) for p in itertools.permutations(themes)})
core_theme={m:r['id'] for r in catalog['themed_routes']['routes'] for m in r['sequence']}
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
gen=(u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)).spawn_actor_from_class(u.AuthoredDungeonGenerator,u.Vector(),transient=True)
bankfile=ROOT/'Config/layout-bank.json'
digest=runpy.run_path(str(PROJECT/'SourceAssets/DungeonFacilityFlow20261007/restore_entry_recipe.py'))['contract_hash'](catalog)
bank=json.loads(bankfile.read_text('utf8')) if bankfile.exists() else dict(version=1,entries={})
if bank.get('contract_sha1',digest)!=digest:bank=dict(version=1,entries={})
bank.update(contract_sha1=digest,native_replay_pending=False,source='offline_native_production_bake_20261010',gameplay_tested=False)
progress=ROOT/'Receipts/layout-bake.json'
first_attempt=(json.loads(progress.read_text('utf8')).get('pass_index',-1)+1) if progress.exists() else 0
failures={};fields=('module','route','origin','yaw','scale','active_ports','link_cm','link_turns','theme_bridge')
receipt=dict(stage='baking',constructed_entries=len(bank['entries']),required_entries=len(pairs),
             pass_index=first_attempt-1,failures=failures,tested=False,rendered=False,game_run=False)
for attempt in range(first_attempt,first_attempt+8):
 for index,pairing in enumerate(pairs):
  key='|'.join('>'.join(p) for p in pairing)
  if key in bank['entries']:continue
  seed=202610100+index+attempt*1009
  c=copy.deepcopy(catalog);c['facility_flow']['probe_pair_order']=list(sum(pairing,()))
  gen.set_editor_property('module_catalog_json',json.dumps(c,ensure_ascii=False,separators=(',',':')))
  gen.set_editor_property('preview_seed',seed);gen.call_method('GeneratePreview')
  result=json.loads(gen.get_editor_property('layout_description'))
  if result['success']:
   actual={};levels=[]
   for ri in range(1,4):
    route='Route'+str(ri)
    rooms=sorted([p for p in result['pieces'] if p['route']==route and p['module'] in core_theme],key=lambda p:p['mission_depth'])
    actual[route]=[core_theme[rooms[0]['module']],core_theme[rooms[3]['module']]]
    levels.append(rooms[0]['origin'][2]-catalog['start_position'][2])
   pieces=[{k:p[k] for k in fields} for p in result['pieces'] if '_Treasure' not in p['route']]
   bank['entries'][key]=dict(route_pairs=actual,levels_cm=levels,theme_bridges_enabled=result['theme_bridges_enabled'],pieces=pieces,source_seed=seed)
   bankfile.write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
   failures.pop(key,None)
  else:
   failures[key]=dict(seed=seed,reason=result['failure'])
   (ROOT/'Receipts'/('layout-construction-'+str(index)+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
  receipt=dict(stage='baking',constructed_entries=len(bank['entries']),required_entries=len(pairs),pass_index=attempt,failures=failures,
               tested=False,rendered=False,game_run=False)
  (ROOT/'Receipts/layout-bake.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
  print('MEDICAL_LAYOUT_CONSTRUCTED',len(bank['entries']),'/120',key,'ready' if result['success'] else 'retry',flush=True)
 if len(bank['entries'])==len(pairs):break
if len(bank['entries'])!=len(pairs):raise RuntimeError('Placement bank production remains incomplete: '+str(len(bank['entries']))+'/120')
receipt.update(stage='layout_data_saved');(ROOT/'Receipts/layout-bake.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
