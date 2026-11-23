"""Merge only the approved exclusive blade into the live catalogs."""
import runpy
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
ID='rift_piercer';WEAPON='ue_frost_crystal_sword'
copy_rules = runpy.run_path(str(ROOT / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))
OPTION=dict(id=ID,name='裂穹长锋',tier='legendary',weapons=[WEAPON],
    description=copy_rules['MELEE_DESCRIPTIONS'][ID],
    stats={'range_mult':1.10,'attack_speed_mult':1.20},
    effects=[{'text':'攻击距离+10%','benefit':1},{'text':'攻击速度+20%','benefit':1}],
    special_effects=copy_rules['MELEE_SPECIAL'][ID])
def publish(name,transform):
    path=DATA/name;before=path.read_bytes();data=transform(json.loads(before.decode('utf-8-sig')))
    backup=P/'BeforeCatalog'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit '+name)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def option(data):
    options=next(c['options'] for c in data['columns'] if c['key']=='blade_1')
    old=next((o for o in options if o['id']==ID),None)
    if old is None:options.append(OPTION)
    else:old.update(OPTION)
    return data
def model(data):
    exports=json.loads((P/'exports.json').read_text(encoding='utf8'))
    data['slots']['blade_1'][ID]=dict(mesh='/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102/SM_FrostSword_Blade_rift_piercer',location_cm=[0,0,0],interface='frost_hilt_v1',appearance=OPTION['description'],**{k:exports[k] for k in ['trace_base_cm','trace_tip_cm','rune_dimensions_cm']})
    return data
if __name__=='__main__':
    if not json.loads((P/'import-receipt.json').read_text(encoding='utf8')).get('assets_saved'):raise RuntimeError('Assets must be saved first')
    publish('melee-gunsmith.json',option);publish('frost-sword-modules.json',model)
    shutil.copy2(P/'Export/RiftPiercer_Icon_Framed.png',DATA/'AttachmentIcons20260913'/f'{WEAPON}_blade_1_{ID}.png')
    print('RIFT_PIERCER_CATALOG_SAVED')
