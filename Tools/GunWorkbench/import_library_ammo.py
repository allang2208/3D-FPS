"""Update the currently referenced workbench, retaining existing placed-instance references."""
import json,re,shutil
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/GunWorkbenchAmmo20260928'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
TARGET='/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench'
DEST=TARGET.rsplit('/',1)[0]
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop PIE before updating the workbench asset')
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entry=next(e for e in palette.get_editor_property('components') if str(e.get_editor_property('id'))=='gun_workbench_table')
previous=entry.get_editor_property('mesh')
if previous.get_path_name()!=MAN['target_mesh']:raise RuntimeError('Active bench reference changed; preserved current asset')
nanite=previous.get_editor_property('nanite_settings')
backup=ROOT/'Before';backup.mkdir(exist_ok=True)
original=P/'Content'/Path(TARGET.removeprefix('/Game/')+'.uasset')
if not (backup/original.name).exists():shutil.copy2(original,backup/original.name)
def canon(name):return re.sub(r'[._][0-9]{3}$','',str(name))
materials={}
for alias,path in MAN['material_paths'].items():
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Retained material missing: '+path)
    materials[alias]=mat
for alias,source in MAN['library_materials'].items():
    mesh=u.load_asset(source['mesh'])
    slot=next(s for s in mesh.get_editor_property('static_materials') if canon(s.material_slot_name)==canon(source['slot']))
    if not slot.material_interface:raise RuntimeError('Library material missing: '+alias)
    materials[alias]=slot.material_interface
ammo_materials={}
for alias,path in MAN['ammo_materials'].items():
    source=u.load_asset(path)
    if not source:raise RuntimeError('Original ammunition material missing: '+path)
    # Copy only for the bench's Nanite usage flag; retain the original material
    # graph and textures, without changing the shared consumable assets.
    destination=DEST+'/Materials/M_GW_'+alias
    material=u.load_asset(destination) or E.duplicate_loaded_asset(source,destination)
    if not material:raise RuntimeError('Ammo material copy failed: '+path)
    L.set_base_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE,True)
    if not E.save_loaded_asset(material,False):raise RuntimeError('Ammo material save failed')
    materials[alias]=material;ammo_materials[alias]={'source':path,'bench_material':material.get_path_name()}

task=u.AssetImportTask();task.filename=MAN['fbx'];task.destination_path=DEST;task.destination_name='SM_GunWorkbench'
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(TARGET)
if not mesh:raise RuntimeError('Workbench import failed')
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=canon(slot.material_slot_name)
    if key not in materials:raise RuntimeError('Material binding missing: '+key)
    mesh.set_material(index,materials[key])
mesh.set_editor_property('nanite_settings',nanite)
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Workbench save failed')
receipt={'saved':True,'mesh':mesh.get_path_name(),'same_asset_reference':True,'ammo_packages':MAN['ammo_placements'],
    'ammo_materials':ammo_materials,'preserved':['table','original lamp','work mat','five library tools','palette ID and footprint'],
    'new_ammo_geometry_authored':False,'new_textures_authored':False,'tests_run':False,'renders_run':False}
(ROOT/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_AMMO_SAVED '+json.dumps({'saved':True,'mesh':mesh.get_path_name(),'ammo_packages':len(MAN['ammo_placements'])}))
