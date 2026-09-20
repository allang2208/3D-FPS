"""Merge six distinct common options while preserving current unrelated catalog edits."""
import json, shutil
from pathlib import Path
P=Path(__file__).parent;SRC=P.parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
fit=json.loads((P/'rune_fit.json').read_text(encoding='utf-8'))
backup=P/'BeforeSix';backup.mkdir(exist_ok=True)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def preserve(path):
    if path.exists() and not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
restored=read(P/'restored-options.json')
path=DATA/'shared-sword-pommels.json';preserve(path);library=read(path)
library['version']=2;library['interfaces']=['shared_sword_pommel_v1','frost_hilt_v1']
for row in restored:
    library['options'][row['id']]={'mesh':receipt['meshes'][row['id']],'interface':'frost_hilt_v1','appearance':row['name']+' · 剑类通用配重'}
library['finishes'].setdefault('silver',{}).update(receipt['finishes']['silver'])
write(path,library)
profiles={}
for weapon,file in [('ue_rune_sword','rune-sword-modules.json'),('ue_frost_crystal_sword','frost-sword-modules.json')]:
    path=DATA/file;preserve(path);catalog=read(path);previous=catalog['pommel_profile']
    native_origin=list(catalog['slots']['pommel']['factory']['location_cm'])
    fields=['location_cm','rotation_deg','scale','adapter']
    star_profile=previous.get('interfaces',{}).get('shared_sword_pommel_v1') or {key:previous[key] for key in fields if key in previous}
    old_profile={'location_cm':native_origin.copy(),'rotation_deg':[0,0,0],'scale':[1,1,1]}
    if weapon=='ue_rune_sword':
        old_profile['location_cm'][2]-=fit['adapter_length_cm'];old_profile['scale']=[fit['scale']]*3
        old_profile['adapter']={'mesh':receipt['adapter'],'location_cm':native_origin,'interface':'azure_hilt_v1_to_frost_hilt_v1'}
    profile={key:value for key,value in previous.items() if key not in fields}
    profile['interfaces']={'shared_sword_pommel_v1':star_profile,'frost_hilt_v1':old_profile}
    catalog['pommel_profile']=profile;write(path,catalog);profiles[weapon]=profile
path=DATA/'melee-gunsmith.json';preserve(path);catalog=read(path)
column=next(c for c in catalog['columns'] if c['key']=='pommel')
new_ids=set(fit['ids'].values());stars=[];other=[]
for row in column['options']:
    if row['id'] in new_ids:continue
    if row['id'] in fit['ids']:
        row.pop('weapons',None);stars.append(row)
    else:other.append(row)
column['options']=restored+stars+other
column['description']='剑类通用配重锤。六款不同造型和属性可供当前各剑共用，按剑型匹配安装位置、尺寸和材质；原装配重单独保留。'
write(path,catalog)
write(P/'integration_receipt.json',{'shared_options':[{'id':o['id'],'name':o['name']} for o in restored+stars],
    'current_swords':catalog['weapons'],'selection_count_including_factory':7,'profiles':profiles,
    'save_policy':'Preserve current ballast_* selections on both swords; restored old Frost designs have distinct pommel_* IDs. No user saves rewritten.',
    'tests_run':False})
print('SIX_COMMON_POMMELS_INSTALLED',len(restored+stars))
