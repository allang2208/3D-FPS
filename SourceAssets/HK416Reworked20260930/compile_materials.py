"""Finish compilation and save completed HK416 material graphs."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
report={'saved':[],'purpose':'Production material compilation after graph construction'}
for path in json.loads((O/'import_receipt.json').read_text())['materials'].values():
    material=u.load_asset(path)
    u.MaterialEditingLibrary.recompile_material(material)
    if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()],False):raise RuntimeError('Material save failed '+path)
    report['saved'].append(path)
(O/'material_build_receipt.json').write_text(json.dumps(report,indent=2))
print('HK416_COMPLETED_MATERIAL_GRAPHS_COMPILED_AND_SAVED')
