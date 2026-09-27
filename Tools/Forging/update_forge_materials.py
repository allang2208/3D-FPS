"""Save forge steel and thermal effects only; no mesh import or runtime preview."""
import datetime
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Forging'))
from forge_materials import build_material, build_effects, build_sparks, DEST

sparks_only = bool(globals().get('FORGE_SPARKS_ONLY', False)) or '-forgesparksonly' in u.SystemLibrary.get_command_line().lower()
names = ['M_ForgeScaleSpark'] if sparks_only else ['M_ForgeHotSteel', 'M_ForgeScaleSpark', 'M_ForgeFume', 'M_ForgeHeatVeil']
targets = {DEST + '/' + n for n in names}
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
# A failed save can be resumed explicitly for packages authored by that same call.
conflicts = (dirty & targets) - set(globals().get('FORGE_RESUME_DIRTY', ()))
if conflicts:
    raise RuntimeError('Unsaved target material edits; preserving editor work: ' + ', '.join(sorted(conflicts)))
saved = []
materials = [build_sparks()] if sparks_only else [build_material('M_ForgeHotSteel', True)] + build_effects()
for material in materials:
    errors = u.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError(material.get_path_name() + ': ' + str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + material.get_path_name())
    saved.append(material.get_path_name())
receipt = {'saved': saved, 'runtime_tested': False, 'rendered': False}
(ROOT / ('SourceAssets/ForgeHeat20260927/materials-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('FORGE_MATERIALS_SAVED ' + json.dumps(receipt), flush=True)
