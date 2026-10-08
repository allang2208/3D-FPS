import json,shutil
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D=ROOT/'Content/ColdSteelData'
U='/Game/Weapons/XuanChiZhenYue20261004/BladeV3';ID='ue_xuanchi_zhenyue'
receipt=json.loads((P/'import_receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Save BladeV3 assets before publishing')
B=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');B.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((D/name).read_text(encoding='utf-8-sig'))
def write(name,obj):
    path=D/name;shutil.copy2(path,B/name);tmp=path.with_suffix('.xuanchi-v3.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
def asset(name):return U+'/Meshes/'+name+'.'+name
catalog=read('xuanchi-zhenyue-modules.json')
for slot,name in [('blade_1','Blade'),('guard','Guard')]:catalog['slots'][slot]['factory']['mesh']=asset('SM_XuanChi_'+name+'_V3')
catalog['slots']['blade_1']['factory']['appearance']='8 毫米等厚剑身 · 连续剑根 · 云螭浅刻槽与锻钢纹理'
catalog['slots']['guard']['factory']['appearance']='原形护手装饰 · 独立于连续剑身'
catalog['surface_revision']='BladeV3';write('xuanchi-zhenyue-modules.json',catalog)
items=read('items.json');items[ID]['world_mesh']=asset('SM_XuanChi_Complete_V3');write('items.json',items)
(P.parent/'active_revision.json').write_text(json.dumps({'revision':'BladeV3',
    'publish_script':str(P/'publish_catalog.py'),'import_script':str(P/'install_assets.py'),
    'editable':str(P/'XuanChi_BladeV3_Editable.blend')},indent=2))
(P/'catalog_receipt.json').write_text(json.dumps({'complete':True,'backup':str(B),'tested':False},indent=2))
print('XUANCHI_BLADE_V3_CATALOG_SAVED')
