"""Publish only Aurora's new packages, then insert its scoped option into the live bow catalog."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile

src=Path(__file__).resolve().parent
root,batch=(Path(v).resolve() for v in sys.argv[1:3])
imported=json.loads((batch/'imported.json').read_bytes())
icon='bow_frontier_compound_riser_frontier_aurora'
packages=imported['packages']
expected={'T_Aurora_Color','T_Aurora_ORM','T_Aurora_Normal','T_Aurora_Glow','M_Aurora_Frame','SK_Frontier_Aurora',icon}
if set(packages)!=expected:raise ValueError('Incomplete Aurora packages')
def sha(data):return hashlib.sha256(data).hexdigest()
def atomic(path,data,replace=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.aurora-tmp',delete=False) as f:
        f.write(data);temp=Path(f.name)
    try:
        if replace:os.replace(temp,path)
        else:
            try:temp.rename(path)
            except FileExistsError:
                if path.read_bytes()!=data:raise
    finally:temp.unlink(missing_ok=True)

files={}
for k,v in packages.items():
    dest=Path('Content')/v.removeprefix('/Game/').split('.')[0]
    path=batch/'Host'/dest.with_suffix('.uasset')
    if not path.is_file():raise FileNotFoundError(path)
    for part in path.parent.glob(k+'.*'):
        if part.suffix in {'.uasset','.uexp','.ubulk','.uptnl'}:
            files[dest.parent/part.name]=part.read_bytes()
png=Path('Content/ColdSteelData/AttachmentIcons20260913/FramedBows')/(icon+'.png')
files[png]=(src/'Export'/png.name).read_bytes()
for rel,data in files.items():atomic(root/rel,data)
option={'id':'frontier_aurora','name':'极光弓体','weapons':['bow_frontier_compound'],
        'description':'边境复合弓专属传说弓体。','appearance':'拉丝银边沿上下弓架收成羽尖。五块极光彩釉嵌进靛蓝底座，釉下细纹从海绿过渡到冰蓝与淡紫。',
        'visual':{'bow_part_riser_mesh':packages['SK_Frontier_Aurora'],'bow_part_riser_material':'','bow_part_riser_scale':1},
        'stats':{},'special_effects':[]}
catalog=root/'Content/ColdSteelData/bow-gunsmith.json'
orig=catalog.read_bytes()
text=orig.decode('utf-8-sig')
doc=json.loads(text)
riser=next(e for e in doc['columns'] if e['key']=='riser')
existing=next((o for o in riser['options'] if o['id']==option['id']),None)
if not existing:
    cursor=text.index('"id": "'+riser['options'][-1]['id']+'"')
    start=text.rindex('{',0,cursor)
    end=start+json.JSONDecoder().raw_decode(text[start:])[1]
    indent=text[text.rfind('\n',0,start)+1:start]
    eol='\r\n' if '\r\n' in text else '\n'
    item=eol.join(indent+s for s in json.dumps(option,indent=2,ensure_ascii=False).splitlines())
    edited=text[:end]+','+eol+item+text[end:]
    riser['options'].append(option)
    if json.loads(edited)!=doc:raise RuntimeError('Out-of-scope catalog delta')
    before=batch/'Before/bow-gunsmith.json'
    if not before.exists():atomic(before,orig)
    if catalog.read_bytes()!=orig:raise RuntimeError('Catalog advanced during install, retry')
    atomic(catalog,(b'\xef\xbb\xbf' if orig.startswith(b'\xef\xbb\xbf') else b'')+edited.encode(),True)
elif existing!=option:raise RuntimeError('Existing option changed, preserving current work')
receipt={'revision':'AuroraFrameR1','option':option,'tier':'Legendary','skeleton':imported['skeleton'],'lods':imported['lods'],
         'slots':imported['slots'],'package_sha256':{str(r.as_posix()):sha(d) for r,d in files.items()},
         'author':'SourceAssets/FrontierCompoundBow20261122/AuroraFrameR1/Frontier_Aurora.blend',
         'reference':'AuroraReference.png','catalog_before':'Before/bow-gunsmith.json','catalog_sha256':sha(catalog.read_bytes()),
         'runtime_tested':False}
publish=batch/'published.json'
if publish.exists():
    for key in ('build','source_archive'):
        old=json.loads(publish.read_bytes())
        if key in old:receipt[key]=old[key]
atomic(publish,(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n').encode(),True)
print('Published',len(packages),'Aurora packages and the framed UI PNG.')
