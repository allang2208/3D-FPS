"""Add only TangDao's live catalogs, preserving the other weapons and saved instances."""
import copy
import json
import shutil
import runpy
from datetime import datetime
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DATA = ROOT / 'Content/ColdSteelData'
ID = 'ue_tang_dao'
exports = json.loads((P / 'exports.json').read_text(encoding='utf-8'))
surface_bindings_path = P / 'SurfaceV2/bindings.json'
surface_bindings = (json.loads(surface_bindings_path.read_text(encoding='utf-8'))
                    if surface_bindings_path.exists() else None)
D = exports['ue_root']
backup = P / 'Before' / datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True, exist_ok=True)

def read(name):
    return json.loads((DATA / name).read_text(encoding='utf-8-sig'))

def write(name, value):
    path = DATA / name
    if path.exists():
        shutil.copy2(path, backup / name)
    temp = path.with_suffix(path.suffix + '.tangdao.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def asset(name):
    return D + '/Meshes/' + name + '.' + name

holding_orientation = P / 'holding_orientation.json'
bone_mount = (json.loads(holding_orientation.read_text(encoding='utf-8'))['bone_mount']
              if holding_orientation.exists() else read('frost-sword-modules.json')['bone_mount'])

catalog = {'version': 1, 'weapon': ID, 'interface': 'tang_dao_hilt_v1', 'drive_bone': 'WPN_root',
           'arms_mesh': exports['arms_mesh'], 'bone_mount': copy.deepcopy(bone_mount),
           'trace_from_animation': False, 'slots': {},
           'pommel_profile': {'library': 'shared-sword-pommels.json', 'finish': 'frost_bronze', 'interfaces': {}}}
for row in exports['parts']:
    spec = {k: copy.deepcopy(v) for k, v in row.items() if k not in ['slot', 'id', 'mesh', 'triangles']}
    spec.update(mesh=asset(row['mesh']), interface='tang_dao_hilt_v1')
    catalog['slots'].setdefault(row['slot'], {})[row['id']] = spec
blade_extensions = []
for relative in ['YanlingBlade20261002/catalog_extension.py', 'TengyunBlade20261002/catalog_extension.py',
                 'YanlingPommel20261002/catalog_extension.py', 'XuanCloudGuard20261002/catalog_extension.py',
                 'PhoenixFeatherGuard20261002/catalog_extension.py',
                 'TigerPommel20261002/catalog_extension.py',
                 'CloudRune20261002/catalog_extension.py']:
    extension_path = P / relative
    if extension_path.exists():
        extension = runpy.run_path(str(extension_path), run_name='tang_dao_blade_extension')
        if extension['installed']():
            blade_extensions.append(extension)
            extension['add_module'](catalog)
            if surface_bindings:
                extension['add_bindings'](surface_bindings)
for key, row in exports['adapters'].items():
    catalog['pommel_profile']['interfaces'][key] = {
        'location_cm': [0, 0, -22.7-row['depth_cm']], 'rotation_deg': [0, 0, 0], 'scale': [row['scale']]*3,
        'adapter': {'mesh': asset(row['mesh']), 'location_cm': [0, 0, -22.7], 'interface': 'tang_dao_hilt_v1_to_' + key}}
if surface_bindings:
    for slot, choices in surface_bindings['slots'].items():
        for option, materials in choices.items():
            catalog['slots'][slot][option]['materials'] = copy.deepcopy(materials)
    for key, materials in surface_bindings['adapters'].items():
        catalog['pommel_profile']['interfaces'][key]['adapter']['materials'] = copy.deepcopy(materials)
    catalog['pommel_profile']['finish'] = 'tang_dao_surface_v2'
    catalog['surface_revision'] = surface_bindings['revision']
    if surface_bindings.get('rune_surface_revision'):
        catalog['rune_surface_revision'] = surface_bindings['rune_surface_revision']
    library = read('shared-sword-pommels.json')
    library['finishes']['tang_dao_surface_v2'] = copy.deepcopy(surface_bindings['pommel_finish'])
    write('shared-sword-pommels.json', library)
write('tang-dao-modules.json', catalog)

items = read('items.json')
item = copy.deepcopy(items['ue_highland_claymore'])
item.update(id=ID, name='唐刀', type='唐刀', weaponTypeTag='双手刀', icon_fallback='唐刀',
            ue_icon='Icons/' + ID + '.png', modular_sword_catalog='tang-dao-modules.json',
            viewmodel_mesh=exports['arms_mesh'], world_mesh=asset(exports['world_mesh']),
            animation_folder=exports['animation_folder'],
            desc='龙炉工坊为远行护卫锻造的长刀，刀身保留龙纹装饰，护手与裹柄便于双手发力。以连续横斩压迫近敌，接突刺追击；蓄力重斩需要留出起势时间，遇到反击可转入格挡。刀刃、护手、握柄、柄尾与刃面符文均可独立改造。')
items[ID] = item
if surface_bindings:
    item['world_mesh'] = surface_bindings['world_mesh']
    if surface_bindings.get('inventory_icon'):
        item['ue_icon'] = surface_bindings['inventory_icon']
write('items.json', items)
formulas = read('combat-weapon-formulas.json')
formulas[ID] = copy.deepcopy(formulas['ue_highland_claymore'])
formulas[ID]['source'] = 'TANGDAO_SHARED_TWO_HANDED_MELEE_RULES'
write('combat-weapon-formulas.json', formulas)
gunsmith = read('melee-gunsmith.json')
if not any((w.get('id') if isinstance(w, dict) else w) == ID for w in gunsmith['weapons']):
    gunsmith['weapons'].append({'id': ID, 'traits': [
        {'icon': 'mechanic', 'text': '双手持刀，占用副手；普通攻击按两次横斩与一次突刺循环'},
        {'icon': 'mechanic', 'text': '支持蓄力重击、格挡与既有近战技能'},
        {'icon': 'neutral', 'text': '刀刃、护手、握柄、柄尾与刃面符文可独立改造'}]})
for column in gunsmith['columns']:
    for option in column['options']:
        if option['id'] in ['bastion_guard', 'riposte_guard', 'light_guard', 'erosion_rune']:
            if 'weapons' in option and ID not in option['weapons']:
                option['weapons'].append(ID)
for blade_extension in blade_extensions:
    blade_extension['add_option'](gunsmith)
write('melee-gunsmith.json', gunsmith)
(P / 'catalog_receipt.json').write_text(json.dumps({'definition': ID, 'name': item['name'],
    'catalog': str(DATA / 'tang-dao-modules.json'), 'backup': str(backup), 'damage_formula': formulas[ID],
    'tested': False}, ensure_ascii=False, indent=2), encoding='utf-8')
print('TANGDAO_CATALOG_INSTALLED ' + ID)
