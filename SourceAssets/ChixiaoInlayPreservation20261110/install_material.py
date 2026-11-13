"""Repair and save only the active Chixiao blade surface in the current host."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
recipe = runpy.run_path(str(P / 'inlay_material.py'))
path = '/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Materials/' + recipe['SURFACE_NAME']
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Use the active FPSGAME host')
if u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('PIE is running; preserve the current session')
if any(package.get_path_name() == path for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved target material ' + path)
disk = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
backup = P / 'BeforeAssets' / disk.relative_to(ROOT / 'Content')
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(disk, backup)
material = u.load_asset(path)
if not material or not recipe['apply_inlay_protection'](material):
    raise RuntimeError('Active Chixiao finish material was not patched')
errors = u.MaterialEditingLibrary.recompile_material(material)
if errors:
    raise RuntimeError('Shader compilation failed: ' + str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('Material save failed ' + path)
receipt = {'revision': recipe['REVISION'], 'asset': material.get_path_name(),
           'saved': True, 'shader_compile_errors': list(errors), 'game_tested': False,
           'protected': ['red inlay', 'texture brass rails'],
           'channels': ['base color', 'roughness', 'normal', 'metallic', 'anisotropy', 'tangent'],
           'temporal_surface': 'original native PBR; no finish override; unchanged',
           'backup': str(backup)}
(P / 'material-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CHIXIAO_INLAY_MATERIAL_SAVED', material.get_path_name())
