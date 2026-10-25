"""Publish only the saved right-hip quiver belt and native body recipes."""
import hashlib,json,os,shutil,sys,uuid
from pathlib import Path
P=Path(__file__).resolve().parents[2];R=P/'SourceAssets/LeatherQuiverBelt20261025';D=P/'Content/ColdSteelData';KEY='ue_leather_quiver_belt'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
saved=read(R/'saved_assets.json');delivery=read(R/'delivery.json')
if not saved.get('completed') or not read(R/'build_receipt.json').get('completed'):raise RuntimeError('Finish asset saves and native build before publication')
for row in delivery['records']:
    if saved['wear'][row['body']]['lod_source_hashes']!=[sha(v['file']) for v in row['lods']]:raise RuntimeError('Wear source changed after save')
if saved['icon_sha256']!=sha(R/(KEY+'.png')):raise RuntimeError('Save the current icon first')
item=dict(id=KEY,name='皮革箭袋腰带',category='equipment',type='腰带',equipSlot='belt',stack_max=1,maxStack=1,price=0,grid_w=2,grid_h=3,defense=dict(base=0,perEnhance=0),
    bonusStats=dict(bowNockSpeed=.50,bowDrawSpeed=.05),bonusPerEnhance=dict(bowNockSpeed=.02,bowDrawSpeed=.01),enhancement=dict(maxLevel=15),
    desc='野外工坊制作的栗棕皮革腰带，双道挂环将内衬绒面的箭袋悬在右髋，便于右手取箭。袋口包边、分隔衬片与底部加固保留了耐用的手工结构，行走时沉稳地随身摆动。',
    ue_icon='Icons/LeatherQuiverBelt20261025/'+KEY+'.png',icon_fallback='带',world_mesh=saved['pickup']['asset'],world_material='',ue_equipment_icon_mesh='',ue_icon_pitch=0,ue_icon_yaw=0,ue_icon_roll=0)
recipes={}
for row in delivery['records']:
    body=row['body'];path=saved['wear'][body]['asset'];motion=row['quiver_motion']
    keys=['pivot','outward','bounds_min','bounds_max','arrow_up','arrow_tips','arrow_mesh','frequency_hz','damping','max_angle_degrees','max_displacement_cm']
    recipes[body]=dict(slot=10,material='',rig_meshes={body:path},owner_body_meshes={body:path},world_covers=[],fit_reference='ue_st6_tactical_pants',source_revision='LeatherQuiverBelt20261025/right-hip-suspension-v1',quiver_motion={k:motion[k] for k in keys})
changes=[]
for file in ('items.json','modular_outfits.json'):
    path=D/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'));text=raw.decode('utf-8-sig')
    rows=[([],item)] if file=='items.json' else [(['items'],recipes['Jason']),(['body_variants','kaitlin','items'],recipes['Kaitlin'])]
    for parent,value in rows:
        target=data
        for key in parent:target=target[key]
        if KEY in target and target[KEY]!=value:raise RuntimeError('Preserve concurrent quiver edits in '+file)
        text=entries.replace(text,parent+[KEY],value) if KEY in target else entries.insert(text,parent,KEY,value)
    changes.append((path,raw,(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')))
for path,raw,text in changes:
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during preparation '+str(path))
for target in (D/item['ue_icon'],D/'Icons'/(KEY+'.png')):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(KEY+'.png'),target)
for path,raw,text in changes:
    backup=R/'Before'/('right-integration-'+path.name);backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    temp=path.with_name(path.name+'.quiver-'+uuid.uuid4().hex+'.tmp');temp.write_bytes(text)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog writer '+str(path))
    os.replace(temp,path)
report=dict(completed=True,item=item,recipes=recipes,game_integrated=True,developer_menu=['基本调参','生成物品','装备','腰带','皮革箭袋腰带'],configuration_load='Next game instance / pawn BeginPlay',arrows_visual_only=True,arrow_visibility='Replicated body pose family Bow; 5 existing wood-arrow meshes',suspension='Vertex-pinned, critically damped cosmetic spring; 2 degrees and 2 cm travel budget',runtime_tested=False,multiplayer_tested=False)
(R/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('LEATHER_QUIVER_BELT_PUBLISHED',KEY,flush=True)
