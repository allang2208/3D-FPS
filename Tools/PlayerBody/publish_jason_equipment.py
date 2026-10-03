"""Publish only the saved equipment repair, preserving other catalog changes."""
import json
from pathlib import Path
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/JasonEquipmentRepair20261003'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assets=load(ROOT/'assets_saved.json')
# This field is written only after the last asset has been successfully saved.
fallback=assets['static_fallback_transform']
body_path=PROJECT/'Content/ColdSteelData/player_body.json';body=load(body_path)
old_body=body['body_mesh'];body['body_mesh']=assets['base']
pack=body['outfits']['ue_mountain_backpack'];pack['world_mesh']=assets['backpack']
pack['world_static_mesh']=assets['backpack_static'];pack.update(fallback)
outfits_path=PROJECT/'Content/ColdSteelData/modular_outfits.json';outfits=load(outfits_path)
profile=dict(outfits['profiles'][old_body])
profile.update(base=assets['base'],native_bare_skin=assets['base'],
               shirt=assets['ue_field_sweater'],gloves=assets['ue_field_gloves'])
profile['hide_source_materials']=list(dict.fromkeys(profile['hide_source_materials']+[7]))
profile['shirt_covers']=list(dict.fromkeys(profile['shirt_covers']+[7]))
outfits['profiles'][assets['base']]=profile
for key,path in assets.items():
    if key.startswith('ue_'):outfits['items'][key]['rig_meshes']['Jason']=path
for key in ['ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt']:
    coverage=outfits['items'][key]['rig_world_covers']['Jason']
    outfits['items'][key]['rig_world_covers']['Jason']=list(dict.fromkeys(coverage+[7]))
save(body_path,body);save(outfits_path,outfits)
author=PROJECT/'SourceAssets/JasonPlayer20261003'
save(author/'outfit_assets_saved.json',{k:v for k,v in assets.items() if k=='base' or k.startswith('ue_')})
receipt=load(author/'body_saved.json');receipt['body']=assets['base'];receipt['covered_hip_section']=7
save(author/'body_saved.json',receipt)
save(ROOT/'published.json',{'body':assets['base'],'backpack':assets['backpack'],'garments':7,
                           'runtime_tested':False})
print('JASON_EQUIPMENT_REPAIR_PUBLISHED')
