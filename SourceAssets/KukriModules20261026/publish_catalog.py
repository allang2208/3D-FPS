"""Publish only this weapon's assembly/catalog and one definition field."""
import json
import re
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DATA = ROOT / 'Content' / 'ColdSteelData'
source = json.loads((P / 'modules.json').read_text(encoding='utf-8'))
labels = {'blade_1': ('刀身', '原装刀身', '前倾弯曲钢刃，保留锤纹刃面与原有切削轮廓。'),
          'grip': ('握柄', '原装木柄', '木质握面与固定铆钉成组装配，保留现有握持轮廓。'),
          'pommel': ('柄尾', '原装柄尾', '外扩木质尾座与内部刀茎末段，保留挂绳穿孔。'),
          'lanyard': ('挂绳／挂饰', '原装挂绳', '穿过柄尾孔的短挂绳，安装位置跟随柄尾。'),
          'blade_2': ('刀身符文', '无附加符文', '保留原有锤纹刀面，不添加额外符文。')}
catalog = {'version': 1, 'weapon': 'ue_kukri', 'columns': []}
assembly = {'version': 1, 'interface': 'kukri-grip-frame-v1-20261026',
            'root_slot': 'blade_1', 'module_slots': ['blade_1', 'grip', 'pommel', 'lanyard'],
            'arms_mesh': '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms.SK_FrostSword_Arms',
            'bone_mount': {'rotation_xyzw': [0, 0, 0, 1], 'location_cm': [0, 0, 0], 'scale': [.01, .01, .01]},
            'slots': {}}
for slot, (label, default, desc) in labels.items():
    column = {'key': slot, 'name': label, 'default': default, 'description': desc, 'options': []}
    if slot == 'lanyard':
        column['options'].append({'id': 'no_lanyard', 'name': '无挂绳',
            'description': '卸下挂绳，保留柄尾穿孔。', 'appearance': '原装柄尾 · 空置穿孔',
            'effects': [], 'stats': {}})
    catalog['columns'].append(column)
    if slot == 'blade_2':
        assembly['slots'][slot] = {'factory': {'appearance': desc}}
        continue
    part = source['parts'][slot]
    spec = {'mesh': part['mesh'], 'location_cm': part['origin_cm'], 'appearance': desc}
    if slot == 'blade_1':
        spec.update(trace_base_cm=[0.6, 0, 8], trace_tip_cm=[6.18, 0, 26.29], rune_dimensions_cm=[10, 2.5, 27])
    if slot == 'lanyard':
        spec['parent_slot'] = 'pommel'
        spec['location_cm'] = [a-b for a,b in zip(part['origin_cm'], source['parts']['pommel']['origin_cm'])]
    assembly['slots'][slot] = {'factory': spec}
    if slot == 'lanyard':
        assembly['slots'][slot]['no_lanyard'] = {'hidden': True, 'appearance': '原装柄尾 · 空置穿孔'}
# Later cosmetic batches own their non-factory entries and base material mappings.
# Rebuilding factory geometry retains those choices and shared option libraries.
existing_modules = DATA / 'kukri-modules.json'
if existing_modules.exists():
    old = json.loads(existing_modules.read_text(encoding='utf-8-sig'))
    for slot in assembly['slots']:
        for key, value in old.get('slots', {}).get(slot, {}).items():
            if key != 'factory':
                assembly['slots'][slot][key] = value
            else:
                for field in ('materials', 'material_slot_names'):
                    if field in value:
                        assembly['slots'][slot]['factory'][field] = value[field]
existing_menu = DATA / 'kukri-gunsmith.json'
if existing_menu.exists():
    old = json.loads(existing_menu.read_text(encoding='utf-8-sig'))
    for column in catalog['columns']:
        previous = next((c for c in old.get('columns', []) if c.get('key') == column['key']), {})
        for key in ('options', 'options_library', 'options_column'):
            if key in previous:
                column[key] = previous[key]
for name, data in [('kukri-modules.json', assembly), ('kukri-gunsmith.json', catalog)]:
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    (P / name).write_text(text, encoding='utf-8')
    (DATA / name).write_text(text, encoding='utf-8')
# Read immediately before merging; preserve every unrelated byte of the shared catalog.
path = DATA / 'items.json'
text = path.read_text(encoding='utf-8-sig')
match = re.search(r'("ue_kukri"\s*:\s*\{)(.*?)(\n\s*\},)', text, re.S)
if not match:
    raise RuntimeError('Missing ue_kukri item definition')
body = match.group(2)
if '"modular_melee_catalog"' not in body:
    start = match.end(1)
    text = text[:start] + '\n                     "modular_melee_catalog": "kukri-modules.json",' + text[start:]
    path.write_text(text, encoding='utf-8')
print('Published kukri-modules.json, kukri-gunsmith.json and ue_kukri.modular_melee_catalog')
