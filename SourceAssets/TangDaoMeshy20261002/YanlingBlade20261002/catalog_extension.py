"""Merge this saved blade into TangDao catalogs without rewriting other choices."""
import copy, json, shutil
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT / 'Content/ColdSteelData'

def installed():
    file = P / 'import_receipt.json'
    return file.exists() and json.loads(file.read_text(encoding='utf-8')).get('complete', False)

def manifest():
    return json.loads((P / 'blade_manifest.json').read_text(encoding='utf-8'))

def add_module(catalog):
    m = manifest()
    fields = ['mesh', 'interface', 'location_cm', 'trace_base_cm', 'trace_tip_cm', 'rune_dimensions_cm', 'materials']
    row = {key: copy.deepcopy(m[key]) for key in fields}
    row['appearance'] = '燕翎折面刀尖、双导槽与层叠锻钢纹；保留原有龙纹。'
    row['combo_third_attack'] = 'sprint_overhead_rectangle'
    catalog['slots']['blade_1'][m['id']] = row
    catalog['yanling_surface_revision'] = 'TangDaoYanlingBlade20261002'

def add_bindings(bindings):
    m = manifest()
    bindings['slots'].setdefault('blade_1', {})[m['id']] = copy.deepcopy(m['materials'])

def add_option(gunsmith):
    m = manifest()
    column = next(c for c in gunsmith['columns'] if c['key'] == 'blade_1')
    option = {'id': m['id'], 'name': m['name'], 'weapons': ['ue_tang_dao'],
              'description': '唐刀专属刀身。燕翎折锋与双槽导势强化连段收尾，第三段改为过顶竖劈，打击前方矩形区域；连续进攻更耗耐力，格挡能力略有降低。',
              'effects': [{'text': '第三段改为冲刺竖劈动作 · 前方矩形判定', 'benefit': 0},
                          {'text': '第三段攻击伤害 +40%', 'benefit': 1},
                          {'text': '攻击耐力消耗 +10%', 'benefit': -1},
                          {'text': '格挡减伤倍率 ×0.90', 'benefit': -1}],
              'stats': {'combo_third_damage_mult': 1.4,
                        'stamina_mult': 1.1, 'block_reduction_mult': .9}}
    for index, old in enumerate(column['options']):
        if old['id'] == m['id']:
            column['options'][index] = option
            break
    else:
        column['options'].append(option)

def install():
    if not installed():
        raise RuntimeError('Save the Yanling mesh, PBR, rune material and icon before installing its option')
    changes = [('tang-dao-modules.json', DATA / 'tang-dao-modules.json', add_module),
               ('melee-gunsmith.json', DATA / 'melee-gunsmith.json', add_option),
               ('bindings.json', P.parent / 'SurfaceV2/bindings.json', add_bindings)]
    for name, path, merge in changes:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        merge(value)
        backup = P / 'Before' / name
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
        temporary = path.with_suffix(path.suffix + '.yanling.tmp')
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    (P / 'catalog_receipt.json').write_text(json.dumps({
        'weapon': 'ue_tang_dao', 'slot': 'blade_1', 'option': 'yanling_edge',
        'saved_assets_required': True, 'runtime_tested': False,
        'combat_stats_changed': True, 'holding_interface_changed': False,
        'third_attack': 'sprint_overhead_rectangle',
        'catalogs': [str(p) for _, p, _ in changes]
    }, indent=2) + '\n', encoding='utf-8')
    print('YANLING_BLADE_OPTION_INSTALLED', flush=True)

if __name__ == '__main__':
    install()
