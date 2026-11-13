"""Apply the user's mid-blade placement choice to both Tengyun variants."""
import json
import runpy
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
apply = runpy.run_path(str(P / 'rune_material.py'))['apply_layout']
mapping = json.loads((ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
targets = []
for family, catalog_name in [('tang_dao', 'tang-dao-modules.json'), ('zhanmadao', 'zhanmadao-modules.json')]:
    catalog = json.loads((ROOT / 'Content/ColdSteelData' / catalog_name).read_text(encoding='utf-8-sig'))
    for source in catalog['slots']['blade_1']['tengyun_dragon']['materials'].values():
        targets.extend([(source, family + '/tengyun_dragon'), (mapping[source], family + '/tengyun_dragon')])
if Path(u.Paths.project_dir()).resolve() != ROOT or u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Use the active host outside PIE')
paths = {path.split('.')[0] for path, _ in targets}
if any(p.get_path_name() in paths for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved target material')
saved = []
for path, profile in targets:
    material = u.load_asset(path)
    if not apply(material, profile):
        raise RuntimeError('Missing rune surface ' + path)
    errors = list(u.MaterialEditingLibrary.recompile_material(material) or [])
    if errors:
        raise RuntimeError(str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Save failed ' + path)
    saved.append(path)
(P / 'centering-receipt.json').write_text(json.dumps({'user_choice': 'preserve aspect; middle of blade',
    'saved_materials': saved, 'game_tested': False}, indent=2) + '\n', encoding='utf-8')
print('DAO_MIDDLE_CENTERING_SAVED', len(saved))
