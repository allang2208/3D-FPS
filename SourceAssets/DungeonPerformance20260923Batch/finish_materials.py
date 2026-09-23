"""Persist Nanite material usage triggered by this batch's mesh production."""
import json, shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[1]
file=ROOT/'Receipts/assets.json';report=json.loads(file.read_text(encoding='utf-8'))
report.setdefault('nanite_materials',{})
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play session')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
materials=set()
for path in report['meshes']:
    mesh=u.load_asset(path)
    for slot in mesh.get_editor_property('static_materials'):
        if slot.material_interface:
            materials.add(slot.material_interface)
            materials.add(slot.material_interface.get_base_material())
for material in sorted(materials,key=lambda m:m.get_path_name()):
    path=material.get_path_name().split('.')[0]
    if path in report['nanite_materials']:continue
    changed=isinstance(material,u.Material) and not material.get_editor_property('used_with_nanite')
    if path not in dirty and not changed:continue
    source=PROJECT/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset')
    dest=ROOT/'Before/Content'/source.relative_to(PROJECT/'Content')
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    if changed:
        material.modify();material.set_editor_property('used_with_nanite',True)
        if u.MaterialEditingLibrary.recompile_material(material):raise RuntimeError('Material build failed '+path)
    if not u.EditorAssetLibrary.save_loaded_asset(material,False):raise RuntimeError('Save failed '+path)
    report['nanite_materials'][path]={'saved':True,'purpose':'Nanite mesh material usage','graph':'unchanged'}
    file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'nanite_materials_saved':len(report['nanite_materials'])}))
