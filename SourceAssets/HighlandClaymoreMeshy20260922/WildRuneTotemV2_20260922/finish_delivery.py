import json
from pathlib import Path
P=Path(__file__).resolve().parent
receipt=json.loads((P/'install_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Material installation is incomplete.')
path=P.parent/'DELIVERY.json';old=path.read_bytes();data=json.loads(old.decode('utf-8-sig'))
wild=data['exclusive_modifications']['wild_rune']
wild['previous_source']='WildRune20260922'
wild['source']=P.name
wild['visual_revision']='Beast-jaw totem V2: unique asymmetric claw cuts and bone spear, dark crimson with local scarlet pulses'
wild['visual_receipt']='WildRuneTotemV2_20260922/install_receipt.json'
wild['material_compile']='Succeeded; saved in the current editor'
wild['native_build_required_for_visual_revision']=False
wild['tested']=False
if path.read_bytes()!=old:raise RuntimeError('Concurrent delivery edit preserved.')
temp=path.with_suffix('.wild-totem-v2.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
print('HIGHLAND_WILD_TOTEM_V2_DELIVERY_RECORDED')
