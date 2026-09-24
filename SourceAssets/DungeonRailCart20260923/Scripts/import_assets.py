"""Reimport only four revised meshes, preserving the installed surface and collision setup."""
import json
import re
import shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Unexpected Unreal project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('PIE is active; preserve this game and defer mesh replacement')
items=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))['objects']
targets={r['asset'] for r in items}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & targets:
    raise RuntimeError('Preserve unsaved edits to target meshes: '+str(sorted(dirty & targets)))

def slot_key(name):
    return re.sub(r'[._][0-9]{3}$','',str(name))

settings={}
for item in items:
    path=item['asset']
    old=u.load_asset(path)
    if old is None:
        raise RuntimeError('Installed mesh missing: '+path)
    materials={slot_key(slot.material_slot_name):slot.material_interface
               for slot in old.get_editor_property('static_materials')}
    for key,fallback in item['materials'].items():
        if materials.get(key) is None:
            materials[key]=u.load_asset(fallback)
        if materials[key] is None:
            raise RuntimeError('Missing surface for '+key)
    body=old.get_editor_property('body_setup')
    settings[path]=dict(materials=materials,nanite=old.get_editor_property('nanite_settings').copy(),
        collision=body.get_editor_property('collision_trace_flag'),
        double_sided=body.get_editor_property('double_sided_geometry'),
        physical_material=body.get_editor_property('phys_material'))
    source=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=ROOT/'Sources/InstalledBeforeRepair'/(path.removeprefix('/Game/')+'.uasset')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        shutil.copy2(source,backup)

receipt=dict(stage='importing',meshes=[],map_modified=False,runtime_tested=False,rendered=False)
receipt_file=ROOT/'Receipts/import.json'
receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
for item in items:
    path=item['asset'];saved=settings[path]
    task=u.AssetImportTask()
    task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI()
    options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=options;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh or not task.get_objects():
        raise RuntimeError('Import did not produce '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        mesh.set_material(index,saved['materials'][slot_key(slot.material_slot_name)])
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',saved['collision'])
    body.set_editor_property('double_sided_geometry',saved['double_sided'])
    body.set_editor_property('phys_material',saved['physical_material'])
    mesh.set_editor_property('nanite_settings',saved['nanite'])
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):
        raise RuntimeError('Could not save '+path)
    receipt['meshes'].append(path)
    receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['stage']='saved'
receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RAIL_CART_IMPORTED',json.dumps(receipt),flush=True)
