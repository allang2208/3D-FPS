"""Rebuild/save only forge blank steel and the two guide routes in-place."""
import importlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/ForgeContrast20261024'
DEST = '/Game/Props/ForgeInteraction20260927'
E = u.EditorAssetLibrary
sys.path.insert(0, str(ROOT / 'Tools/Forging'))
import forge_guide_material
import forge_materials
importlib.reload(forge_guide_material); importlib.reload(forge_materials)
targets = [DEST + '/M_ForgeHotSteel', DEST + '/M_ForgeGuide',
           DEST + '/HammerRefine20261024/M_ForgeHammerGuide', DEST + '/SM_ForgeRing']
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = dirty.intersection(targets)
if conflicts:
    raise RuntimeError('Unsaved target edits preserved: ' + ', '.join(sorted(conflicts)))
for path in targets:
    relative = path.removeprefix('/Game/') + '.uasset'
    before = OUT / 'BeforeAssets' / relative
    before.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'Content' / relative
    if source.exists() and not before.exists(): shutil.copy2(source, before)

saved = []
def save(asset):
    if isinstance(asset, u.Material):
        errors = u.MaterialEditingLibrary.recompile_material(asset)
        if errors: raise RuntimeError(str(errors))
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    saved.append(asset.get_path_name())

steel = forge_materials.build_material('M_ForgeHotSteel', True)
save(steel)
guide = forge_guide_material.build_guide_material(DEST + '/M_ForgeGuide')
save(guide)
hammer_guide = forge_guide_material.build_guide_material(DEST + '/HammerRefine20261024/M_ForgeHammerGuide')
save(hammer_guide)

# Sword/Dao still reference the original ring asset. Give that same asset the
# correctly mapped carrier already used by the hammer/one-handed guide.
source = u.load_asset(DEST + '/HammerRefine20261024/SM_ForgeHammerGuide')
ring = u.load_asset(DEST + '/SM_ForgeRing')
original_slots = ring.get_editor_property('static_materials')
dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
    source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if 'fail' in str(outcome).lower(): raise RuntimeError('Guide carrier read failed: ' + str(outcome))
ring.modify()
_, outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
    dynamic, ring, u.GeometryScriptCopyMeshToAssetOptions(), u.GeometryScriptMeshWriteLOD(), True)
if 'fail' in str(outcome).lower(): raise RuntimeError('Guide carrier write failed: ' + str(outcome))
ring.set_editor_property('static_materials', original_slots)
ring.set_material(0, guide)
settings = ring.get_editor_property('nanite_settings'); settings.enabled = False
ring.set_editor_property('nanite_settings', settings)
save(ring)
receipt = {'saved': saved, 'blank_profiles': ['sword', 'tang_dao', 'warhammer', 'single_handed'],
           'changes': ['Reduced steel incandescence and specular highlight',
                       'Dark backing with opaque black outlines, cyan/white line and center dot',
                       'Exposure-compensated bounded guide colors',
                       'Original sword/Dao ring uses the same correctly mapped carrier'],
           'cpp_changed': False, 'runtime_tested': False, 'rendered': False}
(OUT / 'saved_assets.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('FORGE_CONTRAST_SAVED ' + json.dumps(receipt), flush=True)
