"""Append QBZ definitions without reserializing unrelated shared catalog entries."""
from pathlib import Path
import json,copy,hashlib
O=Path(__file__).parent;root=O.parents[1]
p=root/'Content/ColdSteelData/items.json';raw=p.read_bytes();text=raw.decode('utf-8-sig');items=json.loads(text)
weapon=copy.deepcopy(items['ue_akm']);weapon.update(id='ue_qbz191',name='QBZ-191',desc='QBZ-191 自动步枪，使用独立的 5.8mm 弹药与 30 发标准弹匣。',icon='Icons/ue_qbz191.png',ue_icon='Icons/ue_qbz191.png');weapon['stats'][0]['value']='32'
ammo=copy.deepcopy(items['ammo_556']);ammo.update(id='ammo_58',name='5.8mm 弹药',desc='QBZ-191 使用的 5.8mm 弹药。换弹从背包按发取用，与 5.56mm 和 7.62mm 弹药独立计数。')
new={k:v for k,v in [('ue_qbz191',weapon),('ammo_58',ammo)] if k not in items}
if new:
 end=text.rfind('}');addition=json.dumps(new,ensure_ascii=False,indent=2)[1:-1];updated=text[:end].rstrip()+','+addition+'\n'+text[end:];json.loads(updated);assert p.read_bytes()==raw;p.write_text(updated,encoding='utf-8',newline='')
p=root/'Content/ColdSteelData/gunsmith.json';raw=p.read_bytes();text=raw.decode('utf-8-sig');catalog=json.loads(text)
if not any(w['id']=='ue_qbz191' for w in catalog['weapons']):
 w=copy.deepcopy(next(w for w in catalog['weapons'] if w['id']=='ue_m4a1'));w.update(id='ue_qbz191',model='QBZ-191',name='QBZ-191')
 w['base'].update(ammo_item_id='ammo_58',mag_size=30,damage=32,fire_interval=.085714286,reload_time=2.1,empty_reload_time=164/60)
 # Only the fitted optic is offered. Other M4 geometry/hand poses are not
 # advertised as compatible simply because they exist in the shared catalog.
 w['allowed']=['optic']
 for slot,options in w['options'].items():w['options'][slot]=[o for o in options if o['id']=='false' or slot=='optic' and o['id']=='panoramic_red_dot']
 start=text.index('[',text.index('"weapons"'));_,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length-1
 entry=json.dumps(w,ensure_ascii=False,indent=2);entry='\n'.join('    '+line for line in entry.splitlines())
 updated=text[:end].rstrip()+',\n'+entry+'\n  '+text[end:];json.loads(updated);assert p.read_bytes()==raw;p.write_text(updated,encoding='utf-8',newline='')
(O/'provenance.json').write_text(json.dumps({'archive':'D:/FPS3D/qbz-191-free (1).zip','sha256':hashlib.sha256(Path('D:/FPS3D/qbz-191-free (1).zip').read_bytes()).hexdigest(),'author':'Brahian SG','matching_listing':'https://sketchfab.com/3d-models/qbz-191-free-88786970cb164adaad127a91a29b3dd8','fab_listing':'https://www.fab.com/listings/7b90d34d-2654-4965-8e82-074ea1784e1d','license':'User supplied local model. Archive has no license file; listing text did not expose license terms. No public redistribution of source textures or meshes.','animation':'Adapted existing project M4/Manny motion. Independent QBZ bind and clips; existing source licenses still apply.'},indent=2),encoding='utf-8')
print('QBZ191_DATA_READY')
