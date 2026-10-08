import json,shutil
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D=ROOT/'Content/ColdSteelData';U='/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2';ID='ue_xuanchi_zhenyue'
receipt=json.loads((P/'import_receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Save SurfaceV2 assets before publishing')
B=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');B.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((D/name).read_text(encoding='utf-8-sig'))
def write(name,obj):
    path=D/name;shutil.copy2(path,B/name);tmp=path.with_suffix('.xuanchi-v2.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
def asset(folder,name):return U+'/'+folder+'/'+name+'.'+name
catalog=read('xuanchi-zhenyue-modules.json')
for slot,name in [('blade_1','Blade'),('guard','Guard'),('grip','Grip'),('pommel','Pommel')]:
    catalog['slots'][slot]['factory']['mesh']=asset('Meshes','SM_XuanChi_'+name+'_V2')
catalog['slots']['blade_1']['factory']['appearance']='连续锻钢剑根 · 云螭浅刻槽'
catalog['slots']['guard']['factory']['appearance']='统一缎面钢色 · 连续截面护手接颈'
catalog['slots']['pommel']['factory']['tassel']['materials']={'M_XuanChi_Hilt':asset('Materials','M_XuanChi_Tassel_V2')}
if not catalog.get('pommel_tail_revision'):
    catalog['pommel_profile']['finish']='silver'
for fit in catalog['pommel_profile']['interfaces'].values():
    fit['adapter']['materials']={'M_XuanChi_Mount':asset('Materials','M_XuanChi_Mount_V2')}
catalog['surface_revision']='SurfaceV2';write('xuanchi-zhenyue-modules.json',catalog)
items=read('items.json');items[ID]['world_mesh']=asset('Meshes','SM_XuanChi_Complete_V2')
if receipt.get('inventory_icon'):items[ID]['ue_icon']=receipt['inventory_icon']
write('items.json',items)
(P.parent/'active_revision.json').write_text(json.dumps({'revision':'SurfaceV2','publish_script':str(P/'publish_catalog.py'),'import_script':str(P/'install_assets.py'),'editable':str(P/'XuanChi_SurfaceV2_Editable.blend')},indent=2))
(P/'catalog_receipt.json').write_text(json.dumps({'complete':True,'backup':str(B),'tested':False},indent=2));print('XUANCHI_SURFACE_V2_CATALOG_SAVED')
