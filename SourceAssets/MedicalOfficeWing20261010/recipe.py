"""Scoped formal medical-room replacement and restored infrastructure transitions."""
import copy,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
REVISION='doctor_office_and_intertheme_transitions_20261010'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def apply(catalog,bank=None):
 result=copy.deepcopy(catalog)
 room=read(ROOT/'Config/module.json')
 result['modules']=[m for m in result['modules'] if m['id']!=room['id']]+[room]
 result['room_ids']=list(dict.fromkeys(result['room_ids']+[room['id']]))
 rules=result['themed_routes']
 next(r for r in rules['routes'] if r['id']=='medical')['sequence']=[room['id'],'AbandonedIsolationWard','AbandonedAnatomyTheatre']
 core_rooms={name for r in rules['routes'] for name in r['sequence']}
 core_families={m.get('family_id',m['id']) for m in result['modules'] if m['id'] in core_rooms}
 rules['transition_families']=[f for f in dict.fromkeys(rules['transition_families']+['Drainage']) if f not in core_families]
 rules['forward_only']=[s for s in rules['forward_only'] if s!='Drainage']
 if room['id'] not in rules['forward_only']:rules['forward_only'].append(room['id'])
 rules['inter_theme_transition_count']=1
 rules['transition_placement']='between_complete_three_room_themes'
 drainage=next(m for m in result['modules'] if m['id']=='Drainage')
 drainage.update(encounter_role='facility_transition',selection=dict(chance_per_run=1,max_per_run=2))
 result['facility_flow']['medical_office_revision']=REVISION
 result['facility_flow']['joint_layout_version']=1
 # Geometry and room-slot counts changed. Old positions cannot be relabelled/rehashed.
 result['facility_flow'].pop('layout_bank',None)
 if bank is not None:
  result['facility_flow']['layout_bank']=copy.deepcopy(bank)
  result['facility_flow']['layout_bank']['contract_sha1']=runpy.run_path(str(PROJECT/'SourceAssets/DungeonFacilityFlow20261007/restore_entry_recipe.py'))['contract_hash'](result)
 return result
def reapply_catalog(catalog):
 receipt=ROOT/'Receipts/install.json'
 if not receipt.exists() or read(receipt).get('stage')!='maps_saved':return catalog
 bank=read(ROOT/'Config/layout-bank.json')
 return apply(catalog,bank)
