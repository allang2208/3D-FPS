"""Narrow data updates after saving the new static meshes; do not replace parallel edits."""
import json,os
from pathlib import Path
P=Path(__file__).resolve().parent;data=P.parents[1]/'Content/ColdSteelData'
s=json.loads((P/'saved-assets.json').read_text());assert s['complete'];mesh=s['meshes']
def update(path,func):
    raw=path.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));func(obj)
    txt=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    if b'\r\n' in raw:txt=txt.replace('\n','\r\n')
    encoded=txt.encode('utf-8-sig' if raw[:3]==bytes([239,187,191]) else 'utf-8')
    if encoded==raw:return
    tmp=path.with_suffix('.gale-feather.tmp');tmp.write_bytes(encoded)
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed while preparing edit: '+str(path))
    os.replace(tmp,path)
def mount(d):
    o=d['slots']['guard']['highland_gale_wing']
    def point(obj,key,path):
        if obj[key]!=path and '/GaleWing20261107/' not in obj[key]:raise RuntimeError('Another revision owns '+key)
        obj[key]=path
    point(o,'mesh',mesh['Native']);point(o['mesh_by_blade'],'highland_broadblade',mesh['Broadblade']);point(o['mesh_by_blade'],'highland_ridge_piercer',mesh['Ridge'])
def presentation(d):
    o=next(o for c in d['columns'] if c['key']=='guard' for o in c['options'] if o['id']=='highland_gale_wing')
    o['description']='高地双手剑专属。银钢双翼沿羽脊上扬，翼根的浅金结纹与风誓轻量配重锤相呼应。'
    o['appearance']='上扬银翼、香槟金嵌线与冰蓝菱形宝石'
update(data/'highland-claymore-modules.json',mount)
update(data/'melee-gunsmith.json',presentation)
(P/'catalog.json').write_text(json.dumps({'part':'highland_gale_wing','meshes':mesh,'fields':['mesh','mesh_by_blade','description','appearance'],'saved':True},indent=2))
print('FEATHER_CATALOG_INSTALLED')
