"""Publish the complete saved five-piece workwear set and scoped appearance routes."""
import copy,os,runpy,shutil,sys,uuid
from workwear_common import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import json_entries as entries
saved=read(R/'saved_assets.json');hat=read(R/'Hat/saved_assets.json');display=read(R/'display_assets.json');male=read(R/'authored.json');female=read(R/'female-authored.json');inputs=read(R/'inputs.json')
if not all(d.get('completed') for d in (saved,hat,display,male,female)):raise RuntimeError('Finish all source and asset saves before publication')
if hat.get('fbx_sha256')!=sha(R/'Hat/Exports/FieldHat.fbx'):raise RuntimeError('Save the current boonie FBX before publication')
for row in male['records']+female['records']:
    receipt=saved['saved'][KEY+'/'+row['profile']]
    if receipt['author_sha256']!=sha(row['file']):raise RuntimeError('Save changed jacket source '+row['profile'])
def disk(path):return P/'Content'/(path.split('.')[0][6:]+'.uasset')
for path in [v['asset'] for v in saved['saved'].values()]+[hat['mesh'],hat['pickup'],display['pickup']]:
    if not disk(path).exists():raise RuntimeError('Missing saved package '+path)
D=P/'Content/ColdSteelData';paths=[D/f for f in ('items.json','source-combat-items.json','modular_outfits.json')];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,overlay,cfg=[__import__('json').loads(t) for t in texts]
baseline=read(R/'Before/modular_outfits.json')
for live,old in ((cfg['items'],baseline['items']),(cfg['body_variants']['kaitlin']['items'],baseline['body_variants']['kaitlin']['items'])):
    for key,value in old.items():
        if value.get('slot')!=15:continue
        for field in ('rig_meshes','shoe_fit_meshes'):
            if live[key].get(field)!=value.get(field):raise RuntimeError('Trousers changed during authoring; refresh this waist source before publishing '+key)
members=('ue_cargo_pants','ue_boots','ue_original_gloves','ue_field_hat',KEY)
set_fields=dict(armorSet='workwear',setName='户外工作套装',setBonusDesc='集齐五件：所有动作体力消耗 -15%，移动速度 +10%，饥饿及口渴下降速度 -25%。')
item=dict(id=KEY,name='工装夹克',category='equipment',type='上衣',equipSlot='armor',stack_max=1,maxStack=1,price=55,grid_w=3,grid_h=3,defense=dict(base=8,perEnhance=1.2),desc='灰卡其油蜡帆布夹克，棕皮肩肘补强，蓝色加固缝线与黄铜扣。立体胸袋、斜插手袋和后背活动褶方便野外作业；收腰下摆与内延片衔接裤腰。',ue_icon='Icons/WorkwearSet20261024/'+KEY+'.png',icon_fallback='衣',world_mesh=display['pickup'],world_material='',ue_equipment_icon_mesh='',ue_icon_pitch=0,ue_icon_yaw=0,**set_fields)
catalog_changes={KEY:item}
for key in members[:-1]:
    row=copy.deepcopy(catalog[key]);row.update(set_fields)
    if key=='ue_field_hat':row.update(desc='软冠油蜡帆布奔尼帽，帽冠有自然压褶，窄软檐以多圈压线和包边收束；棕皮帽带、黄铜气眼和后收帽绳与工装夹克搭配。',ue_icon='Icons/WorkwearSet20261024/ue_field_hat.png',ue_equipment_icon_mesh='',world_mesh=hat['pickup'],world_material='',ue_icon_pitch=0,ue_icon_yaw=0)
    catalog_changes[key]=row
for key,value in catalog_changes.items():texts[0]=entries.replace(texts[0],[key],value) if key in catalog else entries.insert(texts[0],[],key,value)
for key in members:
    value=copy.deepcopy(overlay.get(key,{}));value.update(set_fields)
    if key==KEY:value.update(name='工装夹克',defense=item['defense'])
    texts[1]=entries.replace(texts[1],[key],value) if key in overlay else entries.insert(texts[1],[],key,value)
group_by_item={item:g for g,row in inputs['groups'].items() for item in row['items']}
def asset(profile):return saved['saved'][KEY+'/'+profile]['asset']
def recipe_for(rig,current):
    recipe=copy.deepcopy(current)
    for field in ('pants_fit_meshes','pants_mesh_fit_meshes','pants_fit_default'):recipe[field]={}
    recipe['appearance_family']='WorkwearSet20261024';recipe['waist_fit_revision']='20261024-outer-jacket-inner-tuck';recipe['pants_fit_pipeline']='Tools/WorkwearSet/run.ps1';recipe['wear_mode']='outer_jacket_with_inner_tuck'
    # This jacket ends above the older long shirt. Keep the native lower
    # abdomen/hips visible when trousers are removed; trousers own their masks.
    recipe['rig_world_covers'][rig]=[slot for slot in recipe['rig_world_covers'][rig] if slot not in (7,10,14)]
    for profile in recipe['rig_meshes']:
        recipe['rig_meshes'][profile]=asset(rig+'_'+male['default_group']) if profile==rig else asset(profile)
    recipe['owner_body_meshes']={rig:asset('Owner_'+rig+'_'+male['default_group'])}
    def pair(group):return dict(rig_meshes={rig:asset(rig+'_'+group)},owner_body_meshes={rig:asset('Owner_'+rig+'_'+group)})
    garments=cfg['items'] if rig=='Jason' else cfg['body_variants']['kaitlin']['items']
    for key,garment in garments.items():
        if garment.get('slot')!=15:continue
        group=group_by_item[key];recipe['pants_fit_meshes'][key]=pair(group)
        for path in [garment['rig_meshes'][rig]]+[v[rig] for v in garment.get('shoe_fit_meshes',{}).values()]:recipe['pants_mesh_fit_meshes'][path]=pair(group)
    recipe['pants_fit_default']=pair(male['default_group']);return recipe
male_recipe=recipe_for('Jason',inputs['jason_recipe']);female_recipe=recipe_for('Kaitlin',inputs['kaitlin_recipe'])
for path,old,value in [(['items'],cfg['items'],male_recipe),(['body_variants','kaitlin','items'],cfg['body_variants']['kaitlin']['items'],female_recipe)]:texts[2]=entries.replace(texts[2],path+[KEY],value) if KEY in old else entries.insert(texts[2],path,KEY,value)
for key,source in ((KEY,R/(KEY+'.png')),('ue_field_hat',R/'Hat/ue_field_hat.png')):
    destination=D/catalog_changes[key]['ue_icon'];destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
    for fallback in dict.fromkeys([D/'Icons'/(key+'.png')]+([D/catalog[key]['ue_icon']] if key in catalog else [])):
        if fallback.exists():
            backup=R/'Before'/('icon-'+'_'.join(fallback.relative_to(D).parts))
            if not backup.exists():shutil.copy2(fallback,backup)
        fallback.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,fallback)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Shared catalog changed; merge again from current contents')
for path,before,text in zip(paths,raw,texts):
    temp=path.with_name(path.name+'.workwear-'+uuid.uuid4().hex+'.tmp');temp.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
    if path.read_bytes()!=before:raise RuntimeError('Concurrent edit '+str(path))
    os.replace(temp,path)
body_path=D/'player_body.json';before=body_path.read_bytes();body=__import__('json').loads(before.decode('utf-8-sig'));head=copy.deepcopy(body['head_equipment']['ue_field_hat']);head.update(skeletal_mesh=hat['mesh'],fits=hat['fit'],tip_bones=hat['tip_bones'],tip_limit_degrees=8.,tip_frequency_hz=3.,tip_damping=.72,covers_scalp_hair=False)
female_head=copy.deepcopy(body['body_variants']['kaitlin']['head_equipment']['ue_field_hat']);female_head.update(skeletal_mesh=hat['mesh'],tip_bones=hat['tip_bones'],tip_limit_degrees=8.,tip_frequency_hz=3.,tip_damping=.72,covers_scalp_hair=False)
body['head_equipment']['ue_field_hat']=head;body['body_variants']['kaitlin']['head_equipment']['ue_field_hat']=female_head
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'];body_receipt=commit(body_path,before,body,owned_paths=[('head_equipment','ue_field_hat'),('body_variants','kaitlin','head_equipment','ue_field_hat')],producer=__file__)
write(R/'published.json',dict(completed=True,item_name='工装夹克',set_name='户外工作套装',members=members,meshes=len(saved['saved']),body_config=body_receipt,hat_mesh=hat['mesh'],jacket_pickup=display['pickup'],waist_groups=len(inputs['groups']),runtime_tested=False,git_commit=None,git_push=None))
print('WORKWEAR_PUBLISHED',len(saved['saved']),'jacket assets and refined boonie',flush=True)
