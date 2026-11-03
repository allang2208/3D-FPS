"""Persist the three isolated replacement meshes and their two new PBR materials."""
from pathlib import Path
import unreal as u,json
P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/ThunderGodHammer20261028/CommonSeatsStructuralV7'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
if not manifest['complete']:raise RuntimeError('Authoring has not completed')
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=dict(complete=False,models=[],materials=[],saved=[],runtime_tested=False)
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 asset.modify()
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
 receipt['saved'].append(asset.get_path_name());record()
record()
for name,color,metal,rough in [('M_ThorSeatV7_InnerSteel',(.085,.09,.095),.92,.43),('M_ThorSeatV7_Buffer',(.016,.017,.018),.05,.76)]:
 mat=u.load_asset(D+'/'+name)
 if not mat:
  mat=A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
  mat.set_editor_property('used_with_nanite',True)
  mat.set_editor_property('two_sided',True)
  surface=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
  surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
  col=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
  col.set_editor_property('constant',u.LinearColor(*color,1.))
  L.connect_material_expressions(col,'',surface,'BaseColor');L.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
  for value,pin,prop in [(metal,'Metallic',u.MaterialProperty.MP_METALLIC),(rough,'Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
   node=L.create_material_expression(mat,u.MaterialExpressionConstant);node.set_editor_property('r',value)
   L.connect_material_expressions(node,'',surface,pin);L.connect_material_property(node,'',prop)
  L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL)
  L.layout_material_expressions(mat)
  errors=L.recompile_material(mat)
  if errors:raise RuntimeError(str(errors))
 save(mat);receipt['materials'].append(mat.get_path_name());record()

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for row in manifest['parts']:
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
 settings=mesh.get_editor_property('nanite_settings')
 settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
 settings.enabled=True;settings.explicit_tangents=True
 settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.
 mesh.set_editor_property('nanite_settings',settings)
 build=subsystem.get_lod_build_settings(mesh,0)
 build.set_editor_property('use_full_precision_u_vs',True)
 build.set_editor_property('use_high_precision_tangent_basis',True)
 build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True)
 build.set_editor_property('use_mikk_t_space',True)
 subsystem.set_lod_build_settings(mesh,0,build)
 if not u.WarhammerModificationAuditCommandlet.repair_seat_tangent_basis(mesh):raise RuntimeError('Seat tangent repair failed '+mesh.get_path_name())
 save(mesh)
 receipt['models'].append(dict(id=row['id'],mesh=mesh.get_path_name(),appearance=row['appearance'],materials=[s.material_interface.get_path_name() for s in mesh.get_editor_property('static_materials')]))
 record()
receipt['complete']=True;record()
print('THREE_STRUCTURAL_SEATS_SAVED')
