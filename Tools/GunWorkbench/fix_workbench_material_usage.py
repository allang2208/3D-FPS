"""Persist Nanite usage for the current gun bench without replacing any geometry."""
import json,shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/GunWorkbenchVisibleFix20260928'
MESH='/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench'
OWN_MATERIALS={
    '/Game/Building/GunWorkbenchPolish20260928/Materials/M_GW3_Mat.M_GW3_Mat',
    '/Game/Building/GunWorkbenchPolish20260928/Materials/M_GW3_Index.M_GW3_Index'}
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop PIE before saving material assets')
mesh=u.load_asset(MESH)
if not mesh:raise RuntimeError('Current bench asset is missing')
L=u.MaterialEditingLibrary;usage=u.MaterialUsage.MATUSAGE_NANITE
materials={slot.material_interface.get_path_name():slot.material_interface for slot in mesh.get_editor_property('static_materials') if slot.material_interface}
receipt={'mesh':MESH,'saved_materials':[],'unchanged_materials':[], 'game_started':False,'visual_test_run':False}
for path,material in materials.items():
    enabled=L.has_material_usage(material,usage)
    # These two materials may have been auto-enabled in memory by the editor;
    # explicitly persist them as well as fixing any unsupported bound material.
    if enabled and path not in OWN_MATERIALS:
        receipt['unchanged_materials'].append(path);continue
    relative=path.split('.')[0].removeprefix('/Game/')+'.uasset'
    source=PROJECT/'Content'/relative;backup=ROOT/'Before'/relative
    if source.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    material.modify()
    if isinstance(material,u.MaterialInstanceConstant):L.set_material_usage_override(material,usage,True,True)
    else:L.set_base_material_usage(material,usage,True)
    if not u.EditorAssetLibrary.save_loaded_asset(material,False):raise RuntimeError('Material save failed: '+path)
    receipt['saved_materials'].append({'path':path,'previous_nanite_usage':enabled,'saved':True})
    (ROOT/'material-fix.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'material-fix.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_MATERIAL_USAGE_SAVED '+json.dumps(receipt,ensure_ascii=False))
