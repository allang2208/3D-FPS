"""Update/save only the two physical glass materials and their old etching mask."""
from pathlib import Path
from datetime import datetime
import importlib.util,json,shutil,hashlib
import unreal as u
P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('bow_reticle_materials',P/'materials.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
DEST='/Game/Weapons/DarkBow20260925/SingleLensOptics20260927'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('End PIE before saving this material batch')
names=['M_BowOptic_Glass2x','M_BowOptic_Glass4x','M_BowOptic_Etching']
paths=[DEST+'/'+name for name in names]
dirty=[pkg.get_name() for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if pkg.get_name() in paths]
if dirty:raise RuntimeError('Preserve unsaved target materials '+str(dirty))
mats=[u.load_asset(path) for path in paths]
if not all(mats):raise RuntimeError('Current bow optic materials missing')
backup=P/'Before';backup.mkdir(exist_ok=True)
for path in paths:
    original=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
    copy=backup/original.name
    if not copy.exists():shutil.copy2(original,copy)
receipt=P/'apply-receipt.json'
r={'updated':[],'runtime_tested':False,'mesh_reimported':False,
   'shader_sha256':hashlib.sha256((P/'Reticle.hlsl').read_bytes()).hexdigest(),'saved_at':datetime.now().isoformat()}
# Compile/save both lenses before hiding the original subpixel engraving.
for m,power in zip(mats,[2,4,0]):
    if power:author.build_lens(m,power)
    else:author.hide_old_etching(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation failed '+str(errors))
    if not E.save_loaded_asset(m,False):raise RuntimeError('Material save failed '+m.get_path_name())
    r['updated'].append(m.get_path_name());receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
    print('BOW_RETICLE_SAVED',m.get_path_name(),flush=True)
print('BOW_RETICLE_MATERIALS_APPLIED',len(r['updated']))
