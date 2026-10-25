"""Publish saved combat-belt assets without replacing unrelated catalog text."""
import os,shutil,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat_belts_common import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import json_entries as entries

D=P/'Content/ColdSteelData'
execution=read(R/'asset-execution.json')
if execution['exit_code']!=0 or execution['script']!='save_assets.py' or execution['script_sha256']!=sha(P/'Tools/CombatBeltsIntegration/save_assets.py'):
    raise RuntimeError('Finish a successful asset batch before catalog publication')
publications=[]
for which,row in BELTS.items():
    out=R/which;saved=read(out/'saved_assets.json');delivery=read(out/'delivery.json')
    if not saved.get('completed'):raise RuntimeError('Finish saved assets for '+which)
    if saved['source_manifest_sha256']!=sha(out/'delivery.json'):raise RuntimeError('Delivery changed since asset save '+which)
    if saved['icon_sha256']!=sha(out/(row['key']+'.png')):raise RuntimeError('Inventory icon changed since asset save '+which)
    recipe=read(P/'SourceAssets'/row['family']/'stats-proposal.json')['catalog_fields_proposal']
    icon_policy=read(P/'Tools/BeltIcons/policy.json')
    recipe.update({k:icon_policy[k] for k in ('grid_w','grid_h')})
    item=dict(id=row['key'],name=row['name'],category='equipment',type='腰带',stack_max=1,maxStack=1,price=0,
        desc=row['description'],ue_icon='Icons/CombatBelts20261025/'+row['key']+'.png',icon_fallback='带',
        world_mesh=saved['pickup']['asset'],world_material='',ue_equipment_icon_mesh='',ue_icon_pitch=0,ue_icon_yaw=0,ue_icon_roll=0,**recipe)
    wear={}
    for body in ('Jason','Kaitlin'):
        path=saved['wear'][body]['asset']
        wear[body]=dict(slot=10,material='',rig_meshes={body:path},owner_body_meshes={body:path},world_covers=[],
            fit_reference='ue_st6_tactical_pants',source_revision=row['family']+'/IntegrationR1')
    publications.append(dict(which=which,row=row,item=item,wear=wear,saved=saved))

changes=[]
for filename in ('items.json','modular_outfits.json'):
    path=D/filename;before=path.read_bytes();text=before.decode('utf-8-sig');data=read(path)
    for v in publications:
        key=v['row']['key']
        targets=[([],v['item'])] if filename=='items.json' else [(['items'],v['wear']['Jason']),(['body_variants','kaitlin','items'],v['wear']['Kaitlin'])]
        for parent,value in targets:
            target=data
            for segment in parent:target=target[segment]
            if key in target and target[key]!=value:raise RuntimeError('Preserve existing different entry '+filename+' '+key)
            text=entries.replace(text,parent+[key],value) if key in target else entries.insert(text,parent,key,value)
            target[key]=value
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    changes.append((path,before,after))
for path,before,after in changes:
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit; prepare again '+str(path))
for v in publications:
    icon=R/v['which']/(v['row']['key']+'.png')
    for target in (D/v['item']['ue_icon'],D/'Icons'/icon.name):
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(icon,target)
for path,before,after in changes:
    backup=R/'Before'/path.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    temp=path.with_name(path.name+'.combat-belts-'+uuid.uuid4().hex+'.tmp');temp.write_bytes(after)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog writer; retain '+str(path))
    os.replace(temp,path)
for v in publications:
    row=v['row'];out=R/v['which']
    write(out/'published.json',dict(completed=True,item=v['item'],recipes=v['wear'],game_integrated=True,
        developer_menu=['基本调参','生成物品','装备','腰带',row['name']],configuration_load='Next game instance / pawn BeginPlay',
        equip_slot=10,owner_and_world_meshes=True,replication='Existing authoritative inventory and SetWorldOutfit',
        persistence='Existing item definition, enhancement level and instance data',new_storage_capacity=False,
        runtime_tested=False,multiplayer_tested=False))
    stats_path=P/'SourceAssets'/row['family']/'stats-proposal.json';stats=read(stats_path)
    stats.update(stage='published_to_game_catalog',item_catalog_published=True,integration_receipt=str(out/'published.json'))
    for key in ('integration_status','stamina_formula_policy'):
        if key in stats:stats[key]['item_catalog_published']=True
    if v['which']=='arcane':
        stats['formula_integration_note_zh']='腰带已注册到物品目录与男女穿戴配方。法力减耗采用单件内部相加、不同装备及其他乘区相乘，单件减耗上限 50%，最终费用下限为基础值的 20%。冷却属性沿用现有装备与套装乘区。运行与联机由用户测试。'
    write(stats_path,stats)
    print('COMBAT_BELT_PUBLISHED',row['key'],flush=True)
