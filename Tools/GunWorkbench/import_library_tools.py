"""Import the assembly while binding each copied tool to its original UE material."""
import json,re,shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/GunWorkbenchLibraryTools20260928'
DEST='/Game/Building/GunWorkbenchLibraryTools20260928'
PALETTE='/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop PIE before saving assets')
palette=u.load_asset(PALETTE);entries=list(palette.get_editor_property('components'))
index=next(i for i,e in enumerate(entries) if str(e.get_editor_property('id'))=='gun_workbench_table')
entry=entries[index];previous=entry.get_editor_property('mesh')
if previous.get_path_name()!='/Game/Building/GunWorkbenchCleared20260928/SM_GunWorkbench.SM_GunWorkbench':
    raise RuntimeError('Workbench reference has changed; preserved the current version')
target=DEST+'/SM_GunWorkbench'
if E.does_asset_exist(target):raise RuntimeError('Use a new version path for another mesh revision')
def canon(name):return re.sub(r'[._][0-9]{3}$','',str(name))
materials={}
for alias,path in MAN['material_paths'].items():
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Retained material missing: '+path)
    materials[alias]=mat
originals={}
for alias,source in MAN['library_materials'].items():
    mesh=originals.get(source['mesh'])
    if not mesh:
        mesh=u.load_asset(source['mesh']);originals[source['mesh']]=mesh
    if not mesh:raise RuntimeError('Existing library mesh missing: '+source['mesh'])
    slot=next(s for s in mesh.get_editor_property('static_materials') if canon(s.material_slot_name)==canon(source['slot']))
    if not slot.material_interface:raise RuntimeError('Original tool material missing: '+source['slot'])
    materials[alias]=slot.material_interface

task=u.AssetImportTask();task.filename=MAN['fbx'];task.destination_path=DEST;task.destination_name='SM_GunWorkbench'
task.automated=True;task.replace_existing=False;task.save=False
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(target)
if not mesh:raise RuntimeError('Workbench import failed')
for material in set(materials.values()):
    if u.MaterialEditingLibrary.has_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE):continue
    if isinstance(material,u.MaterialInstanceConstant):
        u.MaterialEditingLibrary.set_material_usage_override(material,u.MaterialUsage.MATUSAGE_NANITE,True,True)
    else:
        u.MaterialEditingLibrary.set_base_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE,True)
    if not E.save_loaded_asset(material,False):raise RuntimeError('Material save failed: '+material.get_path_name())
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=canon(slot.material_slot_name)
    if key not in materials:raise RuntimeError('Original material binding missing: '+key)
    mesh.set_material(i,materials[key])
mesh.set_editor_property('nanite_settings',previous.get_editor_property('nanite_settings'))
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
save(mesh)
backup=ROOT/'Before';backup.mkdir(exist_ok=True)
source=PROJECT/'Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset'
if source.exists():shutil.copy2(source,backup/source.name)
entry.set_editor_property('mesh',mesh);entry.set_editor_property('surface',mesh.get_material(0));entries[index]=entry
palette.modify();palette.set_editor_property('components',entries);save(palette)
receipt={'saved':True,'mesh':mesh.get_path_name(),'palette':PALETTE,'previous_mesh':previous.get_path_name(),
    'reused_tools':MAN['reused_tools'],'original_material_bindings':{alias:materials[alias].get_path_name() for alias in MAN['library_materials']},
    'materials_rebuilt':False,'new_tool_geometry_authored':False,'tests_run':False,'renders_run':False}
(ROOT/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('LIBRARY_TOOLS_WORKBENCH_SAVED '+json.dumps({'saved':True,'mesh':mesh.get_path_name(),'reused_tools':len(MAN['reused_tools'])}))
