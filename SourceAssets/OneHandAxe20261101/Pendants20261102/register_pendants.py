"""Install existing common pendants at the hatchet's measured pommel hole."""
import copy
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
DATA = P.parents[2] / 'Content/ColdSteelData'
icons = json.loads((P / 'icon_import_receipt.json').read_text('utf-8'))
if not icons['complete'] or not icons['saved_to_target_project']:
    raise RuntimeError('Pendant icon assets have not finished saving')
mount = json.loads((P / 'mount.json').read_text('utf-8'))
source = json.loads((DATA / 'kukri-modules.json').read_text('utf-8'))
library = json.loads((DATA / 'shared-knife-component-options.json').read_text('utf-8'))
common = next(c for c in library['columns'] if c['key'] == 'lanyard')['options']
ids = ['knife_lanyard_braid', 'knife_lanyard_tassel', 'knife_lanyard_tag']
options = {o['id']: o for o in common}
fit_receipt = P / 'FitV2/registration_receipt.json'
fitted = json.loads(fit_receipt.read_text('utf-8')) if fit_receipt.exists() else None
fitted_parts = {e['id']: e for e in fitted['parts']} if fitted and fitted['complete'] else {}

module_path = DATA / 'tactical-hatchet-modules.json'
modules = json.loads(module_path.read_text('utf-8'))
modules['module_slots'] = list(dict.fromkeys(modules['module_slots'] + ['lanyard']))
slot = modules['slots'].setdefault('lanyard', {})
slot['factory'] = {'hidden': True, 'appearance': '无挂坠 · 保留柄尾穿绳孔'}
for option_id in ids:
    spec = copy.deepcopy(source['slots']['lanyard'][option_id])
    spec['location_cm'] = mount['location_cm']
    spec['parent_slot'] = 'pommel'
    spec['appearance'] = options[option_id]['appearance']
    if option_id in fitted_parts:
        fitted_spec = fitted_parts[option_id]
        spec.update({k: fitted_spec[k] for k in ['mesh', 'materials', 'material_slot_names', 'location_cm']})
        spec['mount_revision'] = 'HatchetCordFitV2'
        spec['collision_capsules_cm'][0] = [-1.35, 0, -.55, 1.75, 0, -.55, .95]
    slot[option_id] = spec

gunsmith_path = DATA / 'tactical-hatchet-gunsmith.json'
gunsmith = json.loads(gunsmith_path.read_text('utf-8'))
column = next((c for c in gunsmith['columns'] if c['key'] == 'lanyard'), None)
if column is None:
    column = {'key': 'lanyard', 'options': []}
    gunsmith['columns'].append(column)
column.update(name='挂坠', default='无挂坠',
              description='挂坠穿过柄尾孔，安装位置跟随柄尾；可选用通用挂绳与挂饰。',
              options_library='shared-knife-component-options.json', options_column='lanyard')

before = P / 'Before'
before.mkdir(exist_ok=True)
for path, data in [(module_path, modules), (gunsmith_path, gunsmith)]:
    if not (before / path.name).exists():
        shutil.copy2(path, before / path.name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt = {'published': True, 'item_id': 'ue_tactical_hatchet', 'slot': 'lanyard',
           'default': 'factory_hidden', 'shared_option_ids': ids,
           'parent_slot': 'pommel', 'location_cm': slot[ids[0]]['location_cm'],
           'models_materials_physics': 'hatchet_fitted_roots_shared_bodies_and_dynamics' if fitted_parts else 'reuse_existing_kukri_common_pendants',
           'shared_option_icons': ['lanyard_' + i for i in ids],
           'saved_icon_assets': icons['saved_assets'], 'runtime_tested': False}
(P / 'registration_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('HATCHET_COMMON_PENDANTS_REGISTERED count=' + str(len(ids)))
