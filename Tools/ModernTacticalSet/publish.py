"""Publish only the new TS01 items and their measured compatibility routes."""
import copy,json,os,runpy,shutil,sys,uuid,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/Integration';D=P/'Content/ColdSteelData'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json');prepared=read(R/'prepared.json')
if not saved['completed']:raise RuntimeError('Save all production assets before publication')
for row in read(R/'derived.json')['records']:
    if saved['wear'].get(row['kind']+'/'+row['rig'],{}).get('sha256')!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():
        raise RuntimeError('TS01 authoring changed during asset save; resume the asset stage before publication: '+row['kind']+'/'+row['rig'])
names={'vest':('ue_modern_kevlar_vest','凯夫拉防弹衣','上衣','armor','衣',22,120,'土棕色尼龙背心，前襟缝有三个圆角风琴袋。深棕织带沿肩带、腰封和衣片包边延伸。'),
 'helmet':('ue_modern_tactical_helmet','现代战术头盔','头盔','helmet','盔',12,75,'哑光土棕色高切头盔，配有深棕包边、侧导轨和四点下颏带。'),
 'gloves':('ue_modern_tactical_gloves','现代战术手套','手套','gloves','手',8,30,'土棕色全指手套配深褐皮革掌面。手背的圆弧护片逐个覆盖指节，腕口以织带收紧。'),
 'pants':('ue_modern_tactical_pants','现代战术裤','裤装','pants','裤',10,65,'土棕色防撕裂战术裤，裆底拼入深棕弹力布。两侧设有立体口袋，裤脚可随靴型收束。'),
 'boots':('ue_modern_tactical_boots','现代战术靴','鞋靴','boots','靴',8,55,'土棕织物与深褐皮革拼接的中帮战术靴，鞋头带双排压线，鞋底为深色橡胶。')}
V,H,G,T,B=[names[k][0] for k in ['vest','helmet','gloves','pants','boots']]
if '--appearance-only' in sys.argv:
    catalog=D/'items.json';raw=catalog.read_bytes();text=raw.decode('utf-8-sig')
    definitions=json.loads(text)
    for row in prepared['rows']:
        if not row['key']:continue
        key=row['key'];kind=row['kind']
        text=entries.replace(text,[key,'desc'],names[kind][-1])
        text=entries.replace(text,[key,'world_mesh'],saved['displays'][kind]['pickup'])
        text=entries.replace(text,[key,'ue_equipment_icon_mesh'],saved['displays'][kind]['icon_mesh'])
        for destination in [D/definitions[key]['ue_icon'],D/'Icons'/(key+'.png')]:
            tmp=destination.with_suffix('.'+uuid.uuid4().hex+'.tmp')
            shutil.copyfile(row['icon']['png'],tmp);os.replace(tmp,destination)
    tmp=catalog.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    tmp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
    if catalog.read_bytes()!=raw:raise RuntimeError('Catalog changed during tactical appearance update')
    os.replace(tmp,catalog)
    (R/'appearance-published.json').write_text(json.dumps(dict(
        completed=True,revision='R3',items=[row['key'] for row in prepared['rows'] if row['key']],
        native_wear_assets=len(saved['wear']),wear=saved['wear'],displays=saved['displays'],
        icons=saved['icons'],inventory_granted=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
    print('TS01_APPEARANCE_PUBLISHED',flush=True);sys.exit(0)
before={};texts={};docs={}
for name in ['items.json','source-combat-items.json','modular_outfits.json']:
    p=D/name;before[name]=p.read_bytes();texts[name]=before[name].decode('utf-8-sig');docs[name]=json.loads(texts[name])
def patch(name,path,value):
    doc=docs[name];parent=doc
    for key in path[:-1]:parent=parent[key]
    texts[name]=entries.replace(texts[name],path,value) if path[-1] in parent else entries.insert(texts[name],path[:-1],path[-1],value)
    parent[path[-1]]=value
def mesh(kind,rig):return saved['wear'][kind+'/'+rig]['asset']
for row in prepared['rows']:
    if not row['key']:continue
    kind=row['kind'];key,name,typ,slot,fallback,defense,price,desc=names[kind];display=saved['displays'][kind]
    item=dict(id=key,name=name,category='equipment',type=typ,equipSlot=slot,stack_max=1,maxStack=1,price=price,grid_w=row['grid_w'],grid_h=row['grid_h'],defense=dict(base=defense,perEnhance=1.2),desc=desc,ue_icon='Icons/ModernTacticalSet20261113/'+key+'.png',icon_fallback=fallback,world_mesh=display['pickup'],world_material='',ue_equipment_icon_mesh=display['icon_mesh'],ue_icon_pitch=0,ue_icon_yaw=0,ue_icon_roll=0)
    patch('items.json',[key],item)
    patch('source-combat-items.json',[key],dict(name=name,defense=item['defense']))
    for destination in [D/item['ue_icon'],D/'Icons'/(key+'.png')]:destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(row['icon']['png'],destination)
cfg=docs['modular_outfits.json'];compatibility=[]
for prefix,rig in [(['items'],'Jason'),(['body_variants','kaitlin','items'],'Kaitlin')]:
    items=cfg
    for part in prefix:items=items[part]
    previous=copy.deepcopy(items['ue_st6_tactical_pants']);pants=copy.deepcopy(previous);pants.update(appearance_family='ModernTacticalSet20261113',rig_meshes={rig:mesh('pants',rig)})
    variants={previous['rig_meshes'][rig]:mesh('pants',rig)}
    for shoe,route in pants['shoe_fit_meshes'].items():
        kind='pants_short' if shoe=='ue_boots' else 'pants_boot' if shoe=='ue_st6_tactical_boots' else 'pants_high'
        variants[route[rig]]=mesh(kind,rig);route[rig]=mesh(kind,rig)
    pants['shoe_fit_meshes'][B]={rig:mesh('pants_boot',rig)}
    boots=copy.deepcopy(items['ue_st6_tactical_boots']);boots.update(appearance_family='ModernTacticalSet20261113',rig_meshes={rig:mesh('boots',rig)})
    gloves=copy.deepcopy(items['ue_original_gloves']);gloves.update(appearance_family='ModernTacticalSet20261113',rig_meshes={r:mesh('gloves',r) for r in gloves['rig_meshes']})
    vest=dict(slot=7,part='shirt',first_person_mode='body_only',material='',appearance_family='ModernTacticalSet20261113',rig_meshes={rig:mesh('vest',rig)},owner_body_meshes={rig:mesh('vest',rig)},covers=[],world_covers=[],rig_world_covers={rig:[]},wear_mode='outer_armor_above_waist',pants_fit_pipeline='Tools/ModernTacticalSet/derive.py')
    for key,value in [(V,vest),(G,gloves),(T,pants),(B,boots)]:patch('modular_outfits.json',prefix+[key],value)
    for key,recipe in list(items.items()):
        if key in [V,G,T,B]:continue
        if recipe.get('slot')==15 and 'ue_st6_tactical_boots' in recipe.get('shoe_fit_meshes',{}):
            patch('modular_outfits.json',prefix+[key,'shoe_fit_meshes',B],copy.deepcopy(recipe['shoe_fit_meshes']['ue_st6_tactical_boots']))
        if recipe.get('slot')!=7:continue
        # The authored waistband is the unchanged native ST6 waistband. Reuse
        # that exact upper fit, including its independent owner-view geometry.
        if 'ue_st6_tactical_pants' in recipe.get('pants_fit_meshes',{}):
            patch('modular_outfits.json',prefix+[key,'pants_fit_meshes',T],copy.deepcopy(recipe['pants_fit_meshes']['ue_st6_tactical_pants']))
        for old,new in variants.items():
            if old in recipe.get('pants_mesh_fit_meshes',{}):
                patch('modular_outfits.json',prefix+[key,'pants_mesh_fit_meshes',new],copy.deepcopy(recipe['pants_mesh_fit_meshes'][old]));compatibility.append(dict(upper=key,rig=rig,source=old,target=new))
# Byte-level compare-and-swap keeps unrelated concurrent catalog edits intact.
backup=R/'BeforePublish';backup.mkdir(exist_ok=True)
for name,data in before.items():
    if (D/name).read_bytes()!=data:raise RuntimeError('Catalog changed; rerun publication from fresh input: '+name)
for name,text in texts.items():
    p=D/name
    if not(backup/name).exists():(backup/name).write_bytes(before[name])
    tmp=p.with_name(p.name+'.ts01-'+uuid.uuid4().hex+'.tmp');tmp.write_bytes((b'\xef\xbb\xbf' if before[name].startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
    if p.read_bytes()!=before[name]:raise RuntimeError('Concurrent edit '+name)
    os.replace(tmp,p)
p=D/'player_body.json';raw=p.read_bytes();body=json.loads(raw.decode('utf-8-sig'));scopes=[]
for prefix,rig in [(['head_equipment'],'Jason'),(['body_variants','kaitlin','head_equipment'],'Kaitlin')]:
    target=body
    for part in prefix:target=target[part]
    target[H]=dict(static_mesh=mesh('helmet',rig),attach_bone='head',covers_scalp_hair=False,fits={rig.lower():dict(location=[0,0,0],rotation=[0,0,0],scale=[1,1,1])});scopes.append(tuple(prefix+[H]))
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'];receipt=commit(p,raw,body,owned_paths=scopes,producer=__file__)
policy=P/'Tools/GarmentWaist/policies.json';raw=policy.read_text(encoding='utf-8-sig');d=json.loads(raw)
value=dict(mode='outer_armor_above_waist',producer='Tools/ModernTacticalSet/derive.py',source_root='SourceAssets/ModernTacticalSet20261113',requires_native_waist_refresh=False)
raw=entries.replace(raw,['shirts',V],value) if V in d['shirts'] else entries.insert(raw,['shirts'],V,value)
policy.write_text(raw,encoding='utf-8')
(R/'published.json').write_text(json.dumps(dict(completed=True,items=list(names.values()),native_wear_assets=len(saved['wear']),icons=saved['icons'],body_config=receipt,waist_routes=compatibility,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('TS01_PUBLISHED five items and both native body routes',flush=True)
