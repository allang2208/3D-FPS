"""Publish the saved belt item and its two native outfit recipes."""
import hashlib,json,os,shutil,sys,uuid
from pathlib import Path
P=Path(__file__).resolve().parents[2];R=P/'SourceAssets/TacticalMagazineBelt20261024';D=P/'Content/ColdSteelData';KEY='ue_tactical_magazine_belt'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
saved=read(R/'saved_assets.json');delivery=read(R/'delivery.json')
if not saved.get('completed'):raise RuntimeError('Complete UE saves before catalog publication')
if not read(R/'build_receipt.json').get('completed'):raise RuntimeError('Complete the native waist-slot build before publication')
for row in delivery['records']:
    if saved['wear'][row['body']]['lod_source_hashes']!=[sha(v['file']) for v in row['lods']]:raise RuntimeError('Wear source changed after save')
if saved['icon_sha256']!=sha(R/(KEY+'.png')):raise RuntimeError('Save the current inventory icon first')
paths=[v['asset'] for v in saved['wear'].values()]+[saved['pickup']['asset'],saved['icon_texture']]+saved['materials']+list(saved['textures'].values())
for path in paths:
    if not (P/'Content'/(path.split('.')[0][6:]+'.uasset')).exists():raise RuntimeError('Asset package not saved '+path)
item=dict(id=KEY,name='战术弹匣腰带',category='equipment',type='腰带',equipSlot='belt',stack_max=1,maxStack=1,price=0,grid_w=2,grid_h=1,defense=dict(base=0,perEnhance=0),
    bonusStats=dict(reloadSpeed=0.025),bonusPerEnhance=dict(reloadSpeed=0.005),enhancement=dict(maxLevel=15),
    desc='采用双层炭黑织带与分段网眼衬垫的勤务腰带，灰色分体扣具连接两侧弹匣套。四个插槽配有加固织带、内衬及底托，贴合腰线的安装带保留了清晰的装备层次。',
    ue_icon='Icons/TacticalMagazineBelt20261024/'+KEY+'.png',icon_fallback='带',world_mesh=saved['pickup']['asset'],world_material='',ue_equipment_icon_mesh='',ue_icon_pitch=0,ue_icon_yaw=0,ue_icon_roll=0)
recipes={}
for name in ('Jason','Kaitlin'):
    path=saved['wear'][name]['asset'];recipes[name]=dict(slot=10,material='',rig_meshes={name:path},owner_body_meshes={name:path},world_covers=[],fit_reference='ue_st6_tactical_pants',source_revision='TacticalMagazineBelt20261024/native-waist-v1')
changes=[]
for file in ('items.json','modular_outfits.json'):
    path=D/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'));text=raw.decode('utf-8-sig')
    rows=[([],item)] if file=='items.json' else [(['items'],recipes['Jason']),(['body_variants','kaitlin','items'],recipes['Kaitlin'])]
    for parent,value in rows:
        target=data
        for key in parent:target=target[key]
        if KEY in target and target[KEY]!=value:raise RuntimeError('Preserve concurrent belt edits in '+file)
        text=entries.replace(text,parent+[KEY],value) if KEY in target else entries.insert(text,parent,KEY,value)
    changes.append((path,raw,(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')))
for path,raw,text in changes:
    if path.read_bytes()!=raw:raise RuntimeError('Configuration changed; merge current file '+str(path))
for target in (D/item['ue_icon'],D/'Icons'/(KEY+'.png')):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(KEY+'.png'),target)
for path,raw,text in changes:
    backup=R/'Before'/path.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    temp=path.with_name(path.name+'.belt-'+uuid.uuid4().hex+'.tmp');temp.write_bytes(text)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent config writer; preserve '+str(path))
    os.replace(temp,path)
report=dict(completed=True,item=item,recipes=recipes,game_integrated=True,developer_menu=['基本调参','生成物品','装备','腰带','战术弹匣腰带'],configuration_load='Next game instance / pawn BeginPlay',magazines_are_visual_props=True,gameplay_ammo_storage=False,bonus_added=False,runtime_tested=False,git_commit=None,git_push=None)
(R/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TACTICAL_BELT_PUBLISHED',KEY,flush=True)
