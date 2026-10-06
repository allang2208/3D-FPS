"""Add saved armor boots and their fit recipes without touching player saves."""
import copy
import json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ArmoredBoots20261004';D=P/'Content/ColdSteelData'
ID='ue_armored_boots';decoder=json.JSONDecoder()
saved=json.loads((R/'saved_assets.json').read_text());profile=json.loads((R/'profile.json').read_text());base=json.loads((R/'base_fitted.json').read_text())
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[x.decode('utf-8-sig') for x in raw]
catalog,config=[json.loads(x) for x in texts]
if ID in catalog or ID in config['items']:raise RuntimeError('Armored boots are already published; preserve the existing definition')
active=config['profiles'][profile['profile_key']]
if active['base']!=profile['previous_base']:raise RuntimeError('Active Jason base changed during production; saved new assets retained, no publication')
for key,definition in [('jeans','ue_jeans'),('cargo','ue_cargo_pants')]:
    if config['items'][definition]['rig_meshes']['Jason']!=profile['trouser_sources'][key]:raise RuntimeError('Trouser source changed during production: '+definition)

def ws(text,start):
    while text[start].isspace():start+=1
    return start
def span(text,path):
    start=ws(text,0)
    for key in path:
        pos=ws(text,start+1);found=False
        while text[pos]!='}':
            candidate,end=decoder.raw_decode(text,pos);pos=ws(text,end);pos=ws(text,pos+1)
            _,end=decoder.raw_decode(text,pos)
            if candidate==key:start=pos;found=True;break
            pos=ws(text,end)
            if text[pos]==',':pos=ws(text,pos+1)
        if not found:raise KeyError(path)
    _,end=decoder.raw_decode(text,start);return start,end
def replace(text,path,value):
    start,end=span(text,path);line=text.rfind('\n',0,start)+1;indent=len(text[line:start])-len(text[line:start].lstrip())
    lines=json.dumps(value,ensure_ascii=False,indent=2).splitlines();replacement=lines[0]+''.join('\n'+' '*indent+x for x in lines[1:])
    return text[:start]+replacement+text[end:]
def insert(text,path,key,value):
    start,_=span(text,path);line=text.rfind('\n',0,start)+1;indent=len(text[line:start])-len(text[line:start].lstrip())+2
    entry=json.dumps({key:value},ensure_ascii=False,indent=2).splitlines()[1:-1]
    addition='\n'+'\n'.join(' '*(indent-2)+x for x in entry)+','
    return text[:start+1]+addition+text[start+1:]
def expand(values):return list(dict.fromkeys(values+[int(k) for k,parent in base['section_origins'].items() if parent in values]))

item=dict(id=ID,name='灰钢铠甲靴',category='equipment',type='鞋靴',equipSlot='boots',rarity='common',stack_max=1,maxStack=1,
    price=85,grid_w=2,grid_h=3,defense={'base':24},
    desc='灰钢护胫与脚背叠甲覆盖深色皮靴，独立护踝、卷边和侧扣保留活动接缝。高筒内衬可搭配收口长裤。',
    ue_icon='Icons/ue_armored_boots.png',icon_fallback='靴',world_mesh=saved['pickup'],world_material='',
    ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=0)
recipe=dict(slot=13,material='',appearance_family='ArmoredBoots20261004',rig_meshes={'Jason':saved['boots']},rig_world_covers={'Jason':base['armored_boot_covers']})
output_catalog=insert(texts[0],[],ID,item);output_config=texts[1]
updated=copy.deepcopy(active);updated['base']=saved['base'];updated['native_bare_skin']=saved['base']
for key in ['shirt_covers','glove_covers']:
    if key in updated:updated[key]=expand(updated[key])
output_config=replace(output_config,['profiles',profile['profile_key']],updated)
fit_keys={'ue_jeans':'jeans','ue_cargo_pants':'cargo','ue_chainmail_pants':'chainmail'}
changed=[]
for definition,old in config['items'].items():
    value=copy.deepcopy(old);coverage=value.get('rig_world_covers',{})
    if 'Jason' in coverage:coverage['Jason']=expand(coverage['Jason'])
    if definition in fit_keys:value.setdefault('shoe_fit_meshes',{})[ID]={'Jason':saved[fit_keys[definition]]}
    if value!=old:output_config=replace(output_config,['items',definition],value);changed.append(definition)
output_config=insert(output_config,['items'],ID,recipe)
if any(p.read_bytes()!=before for p,before in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; no writes made')
for path,before,text in zip(paths,raw,[output_catalog,output_config]):
    backup=R/(path.stem+'-before.json')
    if not backup.exists():backup.write_bytes(before)
    prefix=b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b''
    path.write_bytes(prefix+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(item=item,recipe=recipe,profile=updated,updated_coverage_or_fits=changed,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('ARMORED_BOOTS_CATALOG_PUBLISHED',ID,flush=True)
