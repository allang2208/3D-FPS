"""Scoped structure reimport; preserve approved carpet, other slots and collision."""
import hashlib,json,runpy,shutil
from datetime import datetime
from pathlib import Path
import unreal as u
root=Path(__file__).parent;project=root.parents[2];base='/Game/Props/GodSpaceLayout20260927'
path=base+'/Meshes/SM_GodSpaceStructure'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Stop this hub PIE before reimporting its walkable structure')
if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved structure edits')
inputs=json.loads((root/'FloorTrim/inputs.json').read_text(encoding='utf8'))
disk=project/'Content/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceStructure.uasset'
if hashlib.sha256(disk.read_bytes()).hexdigest()!=inputs['disk_sha256']:raise RuntimeError('Structure changed since the scoped export; preserve new work')
backup=project/'trash/godspace-floor-trim-20260928'/datetime.now().strftime('%H%M%S')
backup.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup/disk.name)
mesh=u.load_asset(path);original_slots=list(mesh.get_editor_property('static_materials'))
original_materials={str(s.get_editor_property('imported_material_slot_name')):s.get_editor_property('material_interface') for s in original_slots}
nanite=mesh.get_editor_property('nanite_settings')
floor_mat=runpy.run_path(str(root/'build_floor_trim_material.py'))['build']()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False
opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.import_uniform_scale=1
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.reorder_material_to_fbx_order=True
task=u.AssetImportTask();task.filename=str(root/'FloorTrim/SM_GodSpaceStructure_TrimV2.fbx')
task.destination_path=base+'/Meshes';task.destination_name='SM_GodSpaceStructure'
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:raise RuntimeError('Structure reimport failed')
mesh=u.load_asset(path)
slots=list(mesh.get_editor_property('static_materials'));names=[]
for i,slot in enumerate(slots):
    name=str(slot.get_editor_property('imported_material_slot_name'));names.append(name)
    material=floor_mat if name=='Floor satin brass' else original_materials.get(name)
    if not material:raise RuntimeError('Unknown reimported slot '+name)
    mesh.set_material(i,material)
if set(names)!=set(original_materials)|{'Floor satin brass'}:raise RuntimeError('Unexpected structure slots')
mesh.set_editor_property('nanite_settings',nanite)
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
runpy.run_path(str(root/'build_navy_carpet.py'))['configure_carpet_density'](mesh)
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Structure save failed')
record={'complete':True,'asset':path,'backup':str(backup/disk.name),'source':task.filename,
    'slots':[{'slot':s.get_editor_property('imported_material_slot_name').to_string() if hasattr(s.get_editor_property('imported_material_slot_name'),'to_string') else str(s.get_editor_property('imported_material_slot_name')),
        'material':s.get_editor_property('material_interface').get_path_name()} for s in mesh.get_editor_property('static_materials')],
    'triangles':mesh.get_num_triangles(0),'carpet_material_unchanged':True,'map_saved':False,'runtime_tested':False,
    'collision':str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
    'disk_sha256':hashlib.sha256(disk.read_bytes()).hexdigest()}
(root/'FloorTrim/install.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print('FLOOR_TRIM_INSTALLED '+json.dumps(record))
