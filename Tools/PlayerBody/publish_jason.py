"""Publish saved Jason assets into the runtime data catalogs (no engine launch)."""
import json
from pathlib import Path
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/JasonPlayer20261003'
body=json.loads((ROOT/'body_saved.json').read_text())
outfits=json.loads((ROOT/'outfit_assets_saved.json').read_text())
clips=json.loads((ROOT/'retargeted_clips.json').read_text())
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=PROJECT/'Content/ColdSteelData/player_body.json';cfg=load(p)
cfg['body_mesh']=body['body'];cfg['clips']=clips;cfg['pose_scale']=[.9066,.95,.9588]
cfg['weapon_pose_reference_mesh']=load(ROOT/'Before/Content/ColdSteelData/player_body.json')['body_mesh']
groom_root='/Game/AsianMale_Jason/Character/Grooms/'
def groom(name,binding):return {'asset':groom_root+name+'.'+name,'binding':groom_root+binding+'.'+binding}
cfg['default_head']='jason'
equipment_receipt=PROJECT/'SourceAssets/JasonEquipmentRepair20261003/assets_saved.json'
if equipment_receipt.exists():
    equipment=load(equipment_receipt)
    if 'backpack' in equipment and 'static_fallback_transform' in equipment:
        recipe=cfg['outfits']['ue_mountain_backpack']
        recipe['world_mesh']=equipment['backpack']
        recipe['world_static_mesh']=equipment['backpack_static']
        recipe.update(equipment['static_fallback_transform'])
cfg.setdefault('heads',{})['jason']={'mesh':body['head'],'materials':{'lambert1':body['head_face_material']},'default_hair':'curly_fade',
    'grooms':[groom('GA_Eyebrows_M_WideJason','GB_Eyebrows_M_WideJason_SKM_Jason_head_Binding'),
              groom('GA_Eyelashes_S_Sparse_Jason','GB_Eyelashes_S_Sparse_Jason_SKM_Jason_head_Binding')],
    'hair_styles':{'curly_fade':{'grooms':[groom('GA_Hair_S_CurlyFade_Jason','GB_Hair_S_CurlyFade_Jason_SKM_Jason_head_Binding')]},
                   'bald':{'grooms':[]}}}
save(p,cfg)
p=PROJECT/'Content/ColdSteelData/modular_outfits.json';cfg=load(p)
cfg['profiles'][body['body']]={'base':outfits['base'],'native_bare_skin':outfits['base'],
    'shirt':outfits['ue_field_sweater'],'gloves':outfits['ue_field_gloves'],
    'hide_source_materials':[0,1,2,3,4,5,6,7],'shirt_covers':[0,1,3,7],'glove_covers':[2],
    'rig_profile':'Jason','separate_gloves':True}
for key,asset in outfits.items():
    if key=='base':continue
    cfg['items'][key].setdefault('rig_meshes',{})['Jason']=asset
for key,regions in [('ue_field_sweater',[0,1,3,7]),('ue_field_sweater_charcoal',[0,3,7]),('ue_chainmail_shirt',[0,1,3,7])]:
    cfg['items'][key].setdefault('rig_world_covers',{})['Jason']=regions
save(p,cfg)
p=PROJECT/'Config/DefaultGame.ini';s=p.read_text(encoding='utf-8-sig')
section='[/Script/UnrealEd.ProjectPackagingSettings]'
paths=['/Game/Characters/JasonPlayer20261003/Animations','/Game/Characters/ModularOutfit20260924/JasonPlayer20261003',
       '/Game/AsianMale_Jason/Mesh/Head','/Game/AsianMale_Jason/Character/Grooms','/Game/AsianMale_Jason/Material']
for path in paths:
    line='+DirectoriesToAlwaysCook=(Path="'+path+'")'
    if line not in s:s=s.replace(section,section+'\n'+line,1)
p.write_text(s,encoding='utf-8-sig')
(ROOT/'published.json').write_text(json.dumps({'body':body['body'],'head':body['head'],'clips':len(clips),'outfits':len(outfits)-1,
    'head_id':'jason','hair_ids':['curly_fade','bald'],'runtime_tested':False},indent=2))
print('JASON_RUNTIME_DATA_PUBLISHED')
