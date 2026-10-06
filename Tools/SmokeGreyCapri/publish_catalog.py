"""Insert the item and Jason recipe shared by world and owner presentations."""
import importlib.util,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004';D=P/'Content/ColdSteelData'
spec=importlib.util.spec_from_file_location('capri_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_assets.json').read_text());context=json.loads((R/'source_context.json').read_text())
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw]
catalog,config=[json.loads(s) for s in texts];definition='ue_smoke_grey_capri'
if definition in catalog or definition in config['items']:raise RuntimeError('Capri definition already published; no overwrite')
if config['profiles'][context['profile_key']]['base']!=context['base']:raise RuntimeError('Body source changed during production; retain new assets and adapt before publication')
item=dict(id=definition,name='烟灰七分裤',category='equipment',type='裤装',equipSlot='pants',rarity='common',stack_max=1,maxStack=1,
    price=40,grid_w=2,grid_h=3,desc='哑光烟灰棉斜纹七分裤，搭配炭灰短袖 T 恤。收窄裤腿、扁平侧袋、膝部省道和双折裤脚，露出下半段小腿。',
    ue_icon='Icons/'+definition+'.png',icon_fallback='裤',world_mesh=saved['pants_pickup'],world_material='',ue_equipment_icon_mesh=saved['pants_icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
rigs=['Jason']
recipe=dict(slot=15,material='',appearance_family='SmokeGreyCapri20261004',rig_meshes={r:saved['pants'] for r in rigs},rig_world_covers={r:context['pants_covers'] for r in rigs},
    shoe_fit_meshes={shoe:{r:saved['pants_high'] for r in rigs} for shoe in ['ue_armored_boots','ue_leather_boots']})
output=[entries.insert(texts[0],[],definition,item),entries.insert(texts[1],['items'],definition,recipe)]
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; no write made')
for path,before,content in zip(paths,raw,output):
    (R/(path.stem+'-before.json')).write_bytes(before)
    prefix=b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'';path.write_bytes(prefix+content.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(item=item,recipe=recipe,matching_shirt='ue_field_sweater_charcoal',player_saves_changed=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('CAPRI_CATALOG_PUBLISHED',definition,flush=True)
