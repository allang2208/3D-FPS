"""Save the final mid-blade source-aspect layouts on all current dao surfaces."""
import json
import runpy
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
apply = runpy.run_path(str(P / 'rune_material.py'))['apply_layout']
mapping = json.loads((ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
targets = {}
for family, catalog_name in [('tang_dao', 'tang-dao-modules.json'), ('zhanmadao', 'zhanmadao-modules.json')]:
    catalog = json.loads((ROOT / 'Content/ColdSteelData' / catalog_name).read_text(encoding='utf-8-sig'))
    for choice, row in catalog['slots']['blade_1'].items():
        for source in row['materials'].values():
            if 'M_TangDaoBladeRuneSurface' in source:
                targets[source] = family + '/' + choice
                targets[mapping[source]] = family + '/' + choice
host_root = Path(u.Paths.project_dir()).resolve()
pie_worlds = u.EditorLevelLibrary.get_pie_worlds(False)
if host_root != ROOT or pie_worlds:
    raise RuntimeError('Preserve active host: project=' + str(host_root)
        + '; expected=' + str(ROOT) + '; PIE=' + str(len(pie_worlds)))
paths = {path.split('.')[0] for path in targets}
if any(p.get_path_name() in paths for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved target material')
saved = []
for path, profile in targets.items():
    material = u.load_asset(path)
    if not apply(material, profile):
        raise RuntimeError('Missing rune surface ' + path)
    errors = list(u.MaterialEditingLibrary.recompile_material(material) or [])
    if errors:
        raise RuntimeError(str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Save failed ' + path)
    saved.append({'asset': path, 'profile': profile, 'saved': True, 'compile_errors': errors})
    print('DAO_FINAL_LAYOUT_SAVED', len(saved), len(targets))
(P / 'final-layout-receipt.json').write_text(json.dumps({'user_choice': 'preserve aspect; middle of blade',
    'materials': saved, 'game_tested': False}, indent=2) + '\n', encoding='utf-8')
print('DAO_FINAL_LAYOUT_COMPLETE', len(saved))
