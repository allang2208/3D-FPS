import hashlib
import json
import runpy
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
saved = json.loads((P / 'asset-save.json').read_text('utf-8-sig'))
if not saved['saved']:
    raise RuntimeError('Save the material before publishing')
relative = Path('Weapons/Zhanmadao20261018/ChixiaoLegendaryV1/Materials/M_ChixiaoSwordTrail.uasset')
source = P / 'AssetHost/Content' / relative
target = ROOT / 'Content' / relative
target.parent.mkdir(parents=True, exist_ok=True)
for suffix in ('.uasset', '.uexp', '.ubulk', '.uptnl'):
    src, dst = source.with_suffix(suffix), target.with_suffix(suffix)
    if not src.exists():
        continue
    if dst.exists() and hashlib.sha256(src.read_bytes()).digest() != hashlib.sha256(dst.read_bytes()).digest():
        raise RuntimeError('Preserving different existing material package: ' + str(dst))
    if not dst.exists():
        shutil.copy2(src, dst)

extension = runpy.run_path(str(P / 'catalog_extension.py'))
catalog_path = ROOT / 'Content/ColdSteelData/melee-gunsmith.json'
catalog = json.loads(catalog_path.read_text('utf-8-sig'))
option = next(o for c in catalog['columns'] if c['key'] == 'blade_1' for o in c['options'] if o['id'] == 'chixiao')
extension['extend_option'](option)
catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

design_path = P.parent / 'ChixiaoBladeConceptV1/design.json'
design = json.loads(design_path.read_text('utf-8-sig'))
design.update(tier='legendary', stats={'attack_speed_mult': 1.15})
design['effect_proposal'].update(revision=5, passive_attack_speed_mult=1.15,
    heavy_trail='crimson_blade_path', source='../ChixiaoLegendaryV1/', game_tested=False)
design_path.write_text(json.dumps(design, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

(P / 'publication.json').write_text(json.dumps({
    'asset_saved': True, 'published': True, 'material': saved['asset'],
    'tier': 'legendary', 'attack_speed_mult': 1.15,
    'release_stamina_multiplier': 2, 'game_tested': False}, indent=2) + '\n', encoding='utf-8')
print('CHIXIAO_LEGENDARY_CATALOG_AND_MATERIAL_PUBLISHED', flush=True)
