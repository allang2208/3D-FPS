"""Compile and save the deployed thermal materials with RHI; no game or capture."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[3]
DEST = '/Game/Weapons/ThermalScope20261006/Runtime'
OUT = PROJECT / 'SourceAssets/ThermalScopeRuntime20261007/EffectFix'
names = ('M_ThermalScene', 'M_ThermalBody', 'M_ThermalFire')
paths = [DEST + '/' + name for name in names]
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Unexpected project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('An existing Play session owns the materials')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):
    raise RuntimeError('Preserve unsaved thermal material edits')
backup = OUT / ('BeforeMaterials-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True, exist_ok=True)
receipt = {'compiled_and_saved': [], 'game_tested': False, 'rendered': False}
for path in paths:
    source = PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    shutil.copy2(source, backup / source.name)
    material = u.load_asset(path)
    if not isinstance(material, u.Material):
        raise RuntimeError('Missing thermal material: ' + path)
    errors = u.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError('Thermal material compilation failed: ' + path + ': ' + str(errors))
    # The recompile call can return before shader jobs finish. This editor API
    # submits and waits for the material's jobs, without drawing a viewport.
    u.MaterialEditingLibrary.get_statistics(material)
    if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()], False):
        raise RuntimeError('Cannot save thermal material: ' + path)
    receipt['compiled_and_saved'].append(material.get_path_name())
    (OUT / 'material-build.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('THERMAL_MATERIAL_COMPILED_AND_SAVED ' + path)
