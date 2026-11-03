"""Import only the light-seat repair into an isolated package in the live editor."""
from pathlib import Path
import unreal as u,json
P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/ThunderGodHammer20261028/LightSeatWindowFixV8'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
if not manifest['complete']:raise RuntimeError('Authoring incomplete')
row=manifest['parts'][0];A=u.AssetToolsHelpers.get_asset_tools()
receipt=dict(complete=False,models=[],saved=[],runtime_tested=False)
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
record()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
path=D+'/Meshes/'+row['mesh'];mesh=u.load_asset(path)
if not mesh:
 task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'))
 task.destination_name=row['mesh'];task.destination_path=D+'/Meshes'
 task.automated=True;task.save=False;task.replace_existing=False;task.options=opt
 A.import_asset_tasks([task]);mesh=u.load_asset(path)
if not mesh:raise RuntimeError('Import failed '+path)
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
 key=str(slot.material_slot_name);mat=u.load_asset(row['materials'][key])
 if not mat:raise RuntimeError('Missing material '+key)
 mesh.set_material(i,mat)
settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;settings.explicit_tangents=True
settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
build=subsystem.get_lod_build_settings(mesh,0)
build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True)
build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True);build.set_editor_property('use_mikk_t_space',True)
subsystem.set_lod_build_settings(mesh,0,build);mesh.modify()
if not u.WarhammerModificationAuditCommandlet.repair_seat_tangent_basis(mesh):raise RuntimeError('Seat tangent repair failed '+mesh.get_path_name())
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed')
receipt['saved'].append(mesh.get_path_name())
receipt['models'].append(dict(id=row['id'],mesh=mesh.get_path_name(),appearance=row['appearance']))
receipt['complete']=True;record();print('LIGHT_SEAT_WINDOW_REPAIR_SAVED')
import runpy
runpy.run_path(str(P/'publish.py'),run_name='__main__')
