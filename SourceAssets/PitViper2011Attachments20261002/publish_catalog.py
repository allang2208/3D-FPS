"""Publish only Pit Viper's shared attachment options after asset saves."""
import copy, json
from pathlib import Path

O = Path(__file__).parent
P = O.parents[1]
ID = 'ue_pit_viper2011'
DEST = '/Game/Weapons/PitViper2011/Attachments20261002'

def augment_weapon(weapon, catalog):
    donor = next(w for w in catalog['weapons'] if w['id'] == 'ue_m1911')
    for slot in ('optic', 'muzzle', 'magazine', 'tactical'):
        factory = copy.deepcopy(next(o for o in weapon['options'][slot] if o['id'] == 'false'))
        choices = [copy.deepcopy(o) for o in donor['options'][slot] if o['id'] != 'false']
        for option in choices:
            if slot == 'muzzle' and option['id'] == 'brake':
                option['description'] = '紧凑侧孔制退器，通过适配接环连接原厂补偿结构，减轻后坐、提高枪械稳定性。'
            elif slot == 'magazine':
                option['description'] = '沿原厂双排弹匣壳体向下加长，保留插接接口、抓握区与独立底板。'
            elif slot == 'tactical' and option['id'] == 'laser':
                option['description'] = '红色激光镭射，腰射沿发射器方向，开镜时汇聚准星；遇遮挡截断。'
        weapon['options'][slot] = [factory] + choices
        if slot not in weapon['allowed']: weapon['allowed'].append(slot)
    weapon['options']['reargrip'] = copy.deepcopy(catalog['pistol_grip_surface_options'])
    weapon['pistol_grip_surface'] = {'mesh': DEST+'/SM_PitViper2011_GripSurface', 'bone': 'WPN_root'}
    # Preserve saved exclusive treatments when reconstructing the shared family.
    vip = O.parent/'PitViper2011VipGrip20261002'
    if (vip/'import_receipt.json').exists() and json.loads((vip/'import_receipt.json').read_text(encoding='utf8')).get('status') == 'imported_and_saved':
        import importlib.util
        spec = importlib.util.spec_from_file_location('pit_viper_vip_grip_catalog', vip/'publish_catalog.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        weapon = module.augment_weapon(weapon, catalog)
    si = O.parent/'PitViper2011SICompensator20261002'
    if (si/'integration_receipt.json').exists() and json.loads((si/'integration_receipt.json').read_text(encoding='utf8')).get('status') == 'imported_and_saved':
        import importlib.util
        spec = importlib.util.spec_from_file_location('pit_viper_si_compensator_catalog', si/'publish_catalog.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        weapon = module.augment_weapon(weapon, catalog)
    for trait in weapon['traits']:
        if trait.get('text', '').startswith('原厂机械瞄具与补偿结构') or trait.get('text', '').startswith('瞄具、枪口、弹匣'):
            trait['text'] = '瞄具、枪口、弹匣、扳机、握把防滑纹与战术挂件均可改造'
    finish = O.parent/'PitViper2011SurfaceRefine20261003'
    if (finish/'import_receipt.json').exists() and json.loads((finish/'import_receipt.json').read_text(encoding='utf8')).get('status') == 'imported_and_saved':
        import importlib.util
        spec = importlib.util.spec_from_file_location('pit_viper_surface_contract', finish/'surface_contract.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        weapon = module.augment_weapon(weapon)
    return weapon

def publish():
    path = P/'Content/ColdSteelData/gunsmith.json'
    text = path.read_text(encoding='utf-8-sig')
    catalog = json.loads(text)
    weapon = augment_weapon(copy.deepcopy(next(w for w in catalog['weapons'] if w['id'] == ID)), catalog)
    pos = text.index(json.dumps(ID), text.index('"weapons"'))
    start = text.rfind('{', 0, pos)
    _, size = json.JSONDecoder().raw_decode(text[start:])
    result = text[:start]+json.dumps(weapon, ensure_ascii=False, indent=2)+text[start+size:]
    if path.read_text(encoding='utf-8-sig') != text: raise RuntimeError('Gunsmith changed during publication')
    path.write_text(result, encoding='utf8')
    summary = {'weapon': weapon, 'physical_meshes': 11, 'shared_modifications': 13,
        'extended_capacity': weapon['base']['mag_size']+3, 'icons': 'shared FramedFirearms; existing pictograms reused',
        'runtime_tested': False}
    (O/'catalog.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    original = O.parent/'PitViper2011Integration20261002/catalog.json'
    if original.exists():
        cache = json.loads(original.read_text(encoding='utf8'))
        cache.update(weapon=weapon, geometry_options='13 common modifications; 11 fitted meshes; numeric trigger retained')
        original.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf8')
    print('PIT_VIPER_COMMON_CATALOG_PUBLISHED', flush=True)

if __name__ == '__main__': publish()
