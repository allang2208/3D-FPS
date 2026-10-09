"""Keep the installed text-card revision when regenerating the subject/draft."""
import json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'TextCards20261005'
def manifest():
 if not (ROOT/'manifest.json').exists():return None
 receipt=ROOT/'Receipts/install.json'
 state=json.loads(receipt.read_text('utf8')) if receipt.exists() else {}
 if state.get('stage') not in ('assets_saved','map_saved'):
  raise RuntimeError('Complete TextCards20261005/install.py before rebuilding the accepted text-card revision')
 return json.loads((ROOT/'manifest.json').read_text('utf8'))
def patch_world():
 if not manifest():return []
 spec=importlib.util.spec_from_file_location('power_text_cards_revision',ROOT/'install.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.patch_loaded_map()
def remap_draft(draft):
 data=manifest()
 if not data:return draft
 lookup={m['previous_mesh']:m['mesh'] for m in data['meshes']}
 def walk(v):
  if isinstance(v,str):return lookup.get(v,v)
  if isinstance(v,list):return [walk(x) for x in v]
  if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
  return v
 draft=walk(draft)
 draft['text_card_revision']='TextCards20261005'
 draft['module_asset_paths']=sorted(set(draft['module_asset_paths'])|{data['base']+'/Materials/M_Power_TextCards'})
 return draft
