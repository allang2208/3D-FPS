"""Assemble production receipts, not a gameplay or multiplayer acceptance report."""
from pathlib import Path
from datetime import datetime,timezone
import json
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text('utf-8-sig'))
models=read('model_manifest.json');icons=read('presentation.json');assets=read('Receipts/ue-import.json');installed=read('Receipts/installation.json');data=read('Receipts/data-installation.json')
build=read('Receipts/build.json') if (ROOT/'Receipts/build.json').exists() else None
receipt={
 'task':'Medical and ecology collectible materials and shared search loot',
 'updated_utc':datetime.now(timezone.utc).isoformat(),
 'models':[{k:a[k] for k in ('id','name','rarity','grid','stack','source','fbx','glb','triangles_lod0','source_components','actual_dimensions_cm','collision_hulls')} for a in models['assets'].values()],
 'inventory_icons':icons['icons'],
 'saved_ue_assets':assets,
 'installation':installed['stage'],
 'loot':{'medical_fixed_or_candidate_bindings':28,'ecology_fixed_or_candidate_bindings':32,'additional_dynamic_family':'Hospital.Bedside','pools':data['pools'],'bindings':data['bindings'],'first_search_item_count':1,'count_is_shared_across_players':True,'candidate_count_is_not_simultaneous_spawn_count':True},
 'network_changes':[
  'Bedside generated actors retain unique complete storage identities but resolve Hospital.Bedside as their configured loot family.',
  'Bedside children use deterministic peer-identical actor names, net-addressable generated actors, and do not also spawn through actor replication.',
  'Ward placement queries static architecture instead of host/client pawn or monster positions.',
  'Existing authority-only loot, shared container revision, transaction journal, resolved markers, per-run storage and late-join open-state snapshots remain the runtime path.'
 ],
 'new_collectible_rarity_floor':'rare',
 'collectible_recovery_values':{a['id']:a['value'] for a in models['assets'].values()},
 'crafting_implemented':False,
 'recipe_design_reference_only':[
  {'output':'hp_potion_high','ingredients':{'alchemy_pure_base_fluid':1,'alchemy_redvein_extract':1}},
  {'output':'mp_potion_high','ingredients':{'alchemy_pure_base_fluid':1,'alchemy_bluemarrow_crystals':1}},
  {'output':'hp_potion_special','ingredients':{'alchemy_pure_base_fluid':1,'alchemy_redvein_extract':2,'alchemy_active_catalyst':1}},
  {'output':'mp_potion_special','ingredients':{'alchemy_pure_base_fluid':1,'alchemy_bluemarrow_crystals':2,'alchemy_active_catalyst':1}},
  {'future_output':'缓释再生药剂','ingredients':{'alchemy_pure_base_fluid':1,'alchemy_redvein_extract':1,'alchemy_compound_stabilizer':1}},
  {'future_output':'清明药剂','ingredients':{'alchemy_pure_base_fluid':1,'alchemy_silverleaf_essence':1,'alchemy_compound_stabilizer':1}}
 ],
 'builds':build,
 'tests_run':False,'game_started':False,'editor_launched':False,'multiplayer_tested':False,
 'visual_acceptance':'Inventory icons rendered from delivered GLBs; no engine preview or gameplay acceptance run.',
 'glass_rendering':'Hollow geometry with separate glass/liquid slots; UE Thin Translucent approximation, Nanite disabled for these meshes.'}
receipt['stage']='assets_data_and_source_saved'
if build and len(build.get('results',[]))==2 and all(r['exit_code']==0 for r in build['results']):receipt['stage']='assets_data_and_native_builds_complete'
(ROOT/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n','utf8')
print('ALCHEMY_DELIVERY',receipt['stage'])
