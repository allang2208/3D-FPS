"""Merge just the hospital office and scoped ward detailing into live catalog data."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def paths(value):
 if isinstance(value,str) and value.startswith('/Game/'):yield value.split('.')[0]
 elif isinstance(value,dict):
  for item in value.values():yield from paths(item)
 elif isinstance(value,list):
  for item in value:yield from paths(item)
def extend_module(module):
 result=copy.deepcopy(module)
 if result['id']!='AbandonedIsolationWard':return result
 office=json.loads((ROOT/'Config/office.json').read_text('utf8'))
 details=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
 replacements={item['replaces']:item['asset'] for item in details['objects'] if 'replaces' in item}
 result['parts']=[p for p in result['parts'] if not p.get('id','').startswith('HospitalOffice.')]
 for part in result['parts']:
  if part['mesh'] in replacements:
   part['mesh']=replacements[part['mesh']];part['materials']=[]
 result['parts'].extend(copy.deepcopy(office['parts']))
 groups=result['warehouse_containers']['groups']
 result['warehouse_containers']['groups']=[g for g in groups if g['id']!='Hospital.Office.Storage']+[copy.deepcopy(office['group'])]
 art=result.get('wall_art',{})
 art['groups']=[g for g in art.get('groups',[]) if g.get('id') not in ('decontamination','decon_shoe_covers')]
 for group in art['groups']:
  if group.get('id')=='service_notices':
   group['slots']=[s for s in group['slots'] if s.get('id')!='DeconNotice']
   group['max_count']=min(group['max_count'],len(group['slots']))
 result['hospital_doctor_office_revision']=office['revision']
 result['hospital_ward_detail_revision']=1
 result['runtime_assets']=list(dict.fromkeys(result.get('runtime_assets',[])+list(paths(office))+list(replacements.values())))
 return result
