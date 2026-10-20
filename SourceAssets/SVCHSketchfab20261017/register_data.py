"""Register the SVCh in the project's weapon data (offline, no editor).

Mirrors the accepted SVD/rifle entries:
  * Content/ColdSteelData/items.json                 weapon item
  * Content/ColdSteelData/gunsmith.json              gunsmith definition
  * Content/ColdSteelData/combat-weapon-formulas.json damage formula
  * Content/ColdSteelData/modular_outfits.json       V9 arms profile for this viewmodel

Existing values are never rewritten silently: the script refuses when a key it
would add already has different content, unless --force is passed.
"""
import argparse
import json
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
DATA = P / 'Content' / 'ColdSteelData'
DEF = 'ue_svch'
NAME = 'SVCh'
AP = argparse.ArgumentParser()
AP.add_argument('--force', action='store_true')
args = AP.parse_args()

receipt = {'definition': DEF, 'written': [], 'skipped': []}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    receipt['written'].append(str(path.relative_to(P)))


# ---------------------------------------------------------------- items
items_path = DATA / 'items.json'
items = read(items_path)
ITEM = {
    'id': DEF,
    'name': NAME,
    'category': 'weapon',
    'type': '武器',
    'equipSlot': 'weapon',
    'weaponType': 'rifle',
    'weaponTypeTag': '精确射手步枪',
    'isTwoHanded': True,
    'stack_max': 1,
    'grid_w': 5,
    'grid_h': 2,
    'icon': 'Icons/ue_svch.png',
    'ue_icon': 'Icons/ue_svch.png',
    'stats': [
        {'name': '物理攻击', 'value': '88'},
        {'name': '弹匣容量', 'value': '10'},
    ],
    'desc': ('绍尔 308 系精确射手步枪的结构，长护木、顶部全长导轨与镂空枪托，'
             '配 7.62×54R 有底缘弹的十发弹匣。气体直吹让连发后坐可控，'
             '机瞄是低矮的开孔式照门与护罩准星，适合在中等距离上快速补枪；'
             '弹匣容量小，换弹前要先压住火力节奏。'),
}
if DEF in items and not args.force:
    if items[DEF] != ITEM:
        receipt['skipped'].append('items.json already has a different %s' % DEF)
        receipt['conflict'] = True
    else:
        receipt['skipped'].append('items.json already matches')
else:
    items[DEF] = ITEM
    write(items_path, items)

# ---------------------------------------------------------------- gunsmith
gs_path = DATA / 'gunsmith.json'
gs = read(gs_path)
rifle = next(w for w in gs['weapons'] if w['id'] == 'ue_svd')
# Reuse the accepted rifle attachment catalogue verbatim: the SVCh carries the
# same rail / muzzle thread / underbarrel interface family, and shared option ids
# keep the gunsmith, icons and stat rows consistent across rifles.
GS = {
    'id': DEF,
    'model': 'SVCH',
    'name': NAME,
    'allowed': list(rifle['allowed']),
    'base': {
        'ammo_item_id': 'ammo_pkm_762x54r',
        'mag_size': 10,
        'ads_smooth': 11.5,
        'recoil': 118,
        'camera_shake': 102,
        'spread_mult': 4.6,
        'fire_interval': 0.30,
        'reload_time': 3.2,
        'empty_reload_time': 4.3,
        'damage': 88,
        'bullet_speed': 545,
        'effective_range': 320,
        'stability_mult': 1.18,
    },
    'options': json.loads(json.dumps(rifle['options'])),
    'traits': [
        {'icon': 'mechanic', 'text': '半自动；每次扣扳机发射一发，射击间隔约 300 ms，十发弹匣供弹'},
        {'icon': 'mechanic', 'text': '直吹导气；连发后坐回升快，开镜后视角抖动小于同口径长后坐枪型'},
        {'icon': 'special', 'text': '有效射程 320 米，弹速 545 m/s，命中时按物理减伤结算'},
        {'icon': 'drawback', 'text': '没有连发模式，腰射散布偏大，弹匣容量小，连续交火需要换弹间隙'},
        {'icon': 'neutral', 'text': '瞄具、枪口、弹匣、枪托、前握把、战术挂件（战术挂件二）与前照门保险均可改造'},
    ],
}
existing = [w for w in gs['weapons'] if w['id'] == DEF]
if existing and not args.force:
    if existing[0] != GS:
        receipt['skipped'].append('gunsmith.json already has a different %s' % DEF)
        receipt['conflict'] = True
    else:
        receipt['skipped'].append('gunsmith.json already matches')
else:
    gs['weapons'] = [w for w in gs['weapons'] if w['id'] != DEF] + [GS]
    write(gs_path, gs)

# ---------------------------------------------------------------- formula
fw_path = DATA / 'combat-weapon-formulas.json'
fw = read(fw_path)
# SVD's scaling is the family reference for a 7.62x54R precision rifle; the SVCh
# carries slightly more base attack and the same attribute coefficients.
FORMULA = json.loads(json.dumps(fw['ue_svd']))
FORMULA['source'] = 'SVCH_ITEM'
FORMULA['base'] = 50.5
if fw.get(DEF) and not args.force:
    if fw[DEF] != FORMULA:
        receipt['skipped'].append('combat-weapon-formulas.json already differs')
        receipt['conflict'] = True
    else:
        receipt['skipped'].append('formula already matches')
else:
    fw[DEF] = FORMULA
    write(fw_path, fw)

# ---------------------------------------------------------------- outfit
mo_path = DATA / 'modular_outfits.json'
mo = read(mo_path)
KEY = '/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny.SK_SVCH_Manny'
SVD_KEY = ('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/'
           'SK_SVD_ModularStock.SK_SVD_ModularStock')
PROFILE = json.loads(json.dumps(mo['profiles'][SVD_KEY]))
PROFILE['rig_profile'] = 'SVD'
if mo['profiles'].get(KEY) and not args.force:
    if mo['profiles'][KEY] != PROFILE:
        receipt['skipped'].append('modular_outfits.json already differs')
        receipt['conflict'] = True
    else:
        receipt['skipped'].append('outfit profile already matches')
else:
    mo['profiles'][KEY] = PROFILE
    write(mo_path, mo)

(P / 'SourceAssets' / 'SVCHSketchfab20261017' / 'Receipts' / 'data_register.json').write_text(
    json.dumps(receipt, indent=1, ensure_ascii=False), encoding='utf-8')
print('SVCH_DATA_REGISTER', json.dumps(receipt, ensure_ascii=False), flush=True)
if receipt.get('conflict'):
    raise SystemExit(2)
