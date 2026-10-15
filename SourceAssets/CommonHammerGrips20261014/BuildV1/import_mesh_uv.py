"""Save corrected UV/tangents as three new mesh packages; reuse saved materials/icons."""
import unreal as u,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE active; defer asset mutation')
D=runpy.run_path(str(P/'catalog.py'))['MESH_DIR'];BASE='/Game/Weapons/CommonHammerGrips20261014/BuildV1'
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name().startswith(D+'/'):raise RuntimeError('Unsaved target: '+pkg.get_name())
A=u.AssetToolsHelpers.get_asset_tools();receipt={'complete':False,'assets':[],'tested':False,'revision':'UV1'}
materials={'M_SteelWarhammerSurface':u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface')}
for name in ('M_HammerGripWoven','M_HammerGripLeather','M_HammerGripDarkLeather'):materials[name]=u.load_asset(BASE+'/Materials/'+name)
if any(not mat for mat in materials.values()):raise RuntimeError('Saved material missing')
def record():(P/'uv_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record();u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
for row in json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']:
    mesh=u.load_asset(D+'/'+row['mesh'])
    if not mesh:
        task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'));task.destination_path=D;task.destination_name=row['mesh']
        task.automated=True;task.save=False;task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+row['mesh'])
    if not mesh:raise RuntimeError('Mesh import failed: '+row['mesh'])
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,materials[str(slot.material_slot_name)])
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Mesh save failed')
    receipt['assets'].append(mesh.get_path_name());record()
runpy.run_path(str(P/'register_grips.py'),run_name='__main__');receipt['complete']=True;record()
print('COMMON_HAMMER_GRIPS_UV_SAVED')
