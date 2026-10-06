"""Publish only the RSH weapon's new option after its model/icon have saved."""
import json
import re
from pathlib import Path

O=Path(__file__).resolve().parent
P=O.parents[1]
OPTION='rsh12_large_caliber_brake'

def apply_weapon(weapon):
    option=json.loads((O/'option.json').read_text(encoding='utf8'))
    choices=weapon['options']['muzzle']
    existing=next((o for o in choices if o['id']==OPTION),None)
    if existing is not None:existing.update(option)
    else:choices.append(option)
    return option

if __name__=='__main__':
    model=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
    icon=json.loads((O/'icon_receipt.json').read_text(encoding='utf8'))
    if not model.get('complete') or not model.get('lod1_saved'):
        raise RuntimeError('Model / LOD has not finished saving')
    path=P/'Content/ColdSteelData/gunsmith.json'
    raw=path.read_bytes();text=raw.decode('utf-8-sig')
    decoder=json.JSONDecoder();pos=text.index('[',text.index('"weapons"'))+1
    while True:
        while text[pos].isspace() or text[pos]==',':pos+=1
        weapon,end=decoder.raw_decode(text,pos)
        if weapon['id']=='ue_rsh12':break
        pos=end
    option=apply_weapon(weapon)
    indent=re.search(r'[^\S\n]*$',text[:pos]).group()
    replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
    backup=O/'Before/gunsmith.json';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during publication')
    path.write_bytes((text[:pos]+replacement+text[end:]).encode('utf8'))
    (O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',option=option,
        mesh=model['mesh'],icon=icon['texture'],other_weapons_changed=False,
        suppressed=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
    print('RSH_MUZZLE_BRAKE_CATALOG_SAVED',flush=True)
