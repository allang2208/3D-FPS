"""Explicit RSH opt-in to existing common grip patterns, preserving other work."""
import copy,json,re
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]

def apply_weapon(weapon,catalog):
    auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
    weapon['pistol_grip_surface']={'mesh':auth['mesh'],'bone':'WPN_root'}
    if 'reargrip' not in weapon['allowed']:weapon['allowed'].append('reargrip')
    weapon['options']['reargrip']=copy.deepcopy(catalog['pistol_grip_surface_options'])
    return weapon

def publish():
    if not json.loads((O/'import_receipt.json').read_text(encoding='utf8')).get('complete'):
        raise RuntimeError('Save grip mesh before exposing the options')
    path=P/'Content/ColdSteelData/gunsmith.json';before=path.read_text(encoding='utf-8-sig');catalog=json.loads(before)
    decoder=json.JSONDecoder();position=before.index('[',before.index('"weapons"'))+1
    while True:
        while before[position].isspace() or before[position]==',':position+=1
        weapon,end=decoder.raw_decode(before,position)
        if weapon['id']=='ue_rsh12':break
        position=end
    apply_weapon(weapon,catalog)
    indent=re.search(r'[^\S\n]*$',before[:position]).group()
    replacement=json.dumps(weapon,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
    if path.read_text(encoding='utf-8-sig')!=before:raise RuntimeError('Concurrent gunsmith catalog change')
    backup=O/'Before/gunsmith.json';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_text(before,encoding='utf8')
    path.write_text(before[:position]+replacement+before[end:],encoding='utf8')
    (O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',binding=weapon['pistol_grip_surface'],
        options=weapon['options']['reargrip'],icons='existing shared FramedFirearms',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
    print('RSH_GRIP_CATALOG_SAVED',flush=True)

if __name__=='__main__':publish()
