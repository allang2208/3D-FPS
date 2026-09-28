"""Save the workbench with the original full-detail lamp and original materials."""
import json,re,shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
REVISION=globals().get('WORKBENCH_REVISION','GunWorkbenchLampRestore20260928')
ROOT=PROJECT/'SourceAssets'/REVISION
DEST='/Game/Building/'+REVISION
PALETTE='/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
STATE=json.loads((PROJECT/'SourceAssets/GunWorkbenchLampRestore20260928/source-state.json').read_text(encoding='utf-8'))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop PIE before saving assets')
palette=u.load_asset(PALETTE)
entries=list(palette.get_editor_property('components'))
index=next(i for i,e in enumerate(entries) if str(e.get_editor_property('id'))=='gun_workbench_table')
entry=entries[index];previous=entry.get_editor_property('mesh')
expected=('/Game/Building/GunWorkbenchLampRestore20260928/SM_GunWorkbench.SM_GunWorkbench'
          if MAN['other_clutter_removed'] else STATE['palette_mesh']['path'])
if previous.get_path_name()!=expected:raise RuntimeError('Workbench reference changed since the scoped read; preserved current asset')
target=DEST+'/SM_GunWorkbench'
if E.does_asset_exist(target):raise RuntimeError('Use a new version path instead of reimporting an already saved combined mesh')

task=u.AssetImportTask();task.filename=MAN['fbx'];task.destination_path=DEST;task.destination_name='SM_GunWorkbench'
task.automated=True;task.replace_existing=False;task.save=False
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task])
mesh=u.load_asset(target)
if not mesh:raise RuntimeError('Mesh import failed')
def canon(name):return re.sub(r'[._][0-9]{3}$','',str(name))
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    path=MAN['material_paths'].get(canon(slot.material_slot_name))
    material=u.load_asset(path) if path else None
    if not material:raise RuntimeError('Original material missing: '+str(slot.material_slot_name))
    mesh.set_material(i,material)
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
    'original_lamp_copied':MAN['lamp_copies'],'clutter_removed':MAN['other_clutter_removed'],
    'materials_rebuilt':False,'renders_run':False,'game_started':False,
    'scope':'Replace derived lamp geometry with unchanged original lamp and flex; retain prefab contracts.'}
(ROOT/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('ORIGINAL_WORKBENCH_LAMP_SAVED '+json.dumps({'saved':True,'mesh':mesh.get_path_name(),'clutter_removed':MAN['other_clutter_removed']}))
