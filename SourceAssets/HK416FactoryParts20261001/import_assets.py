"""Import production AR fits and reuse the existing 416 part icons; save only these packages."""
import unreal as u,json,re
from pathlib import Path
from runpy import run_path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/HK416/ARParts20261001';H='/Game/Weapons/HK416/Reworked20260930'
apply_m16_bindings=run_path(str(O.parent/'WeaponSurface20260930/M16/current_bindings.py'))['apply_current_bindings']
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=P.resolve():raise RuntimeError('Wrong project for AR furniture publication')
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
models=json.loads((O/'models.json').read_text(encoding='utf-8'))
receipt={'meshes':{},'icons':{},'testing':'Not run; production import and save only'}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
 asset=u.load_asset(path)
 if not asset:raise RuntimeError('Missing source asset '+path)
 return asset
def save(asset):
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Save failed '+asset.get_path_name())
def canonical(name):return re.sub(r'[._]\d{3}$','',str(name))
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,part in models['parts'].items():
  donor=load(H+'/Attachments/SM_HK416_'+part['source_key'])
  bindings={canonical(s.material_slot_name):s.material_interface for s in donor.static_materials}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
  opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task=u.AssetImportTask();task.filename=part['fbx'];task.destination_path=D+'/'+part['family'];task.destination_name=part['name'];task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
  A.import_asset_tasks([task]);mesh=load(task.destination_path+'/'+part['name']);slots=list(mesh.static_materials)
  for i,slot in enumerate(slots):
   slot.material_interface=bindings[canonical(slot.material_slot_name)];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  apply_m16_bindings(mesh)
  slots=list(mesh.static_materials)
  editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
  settings=editor.get_lod_build_settings(mesh,0)
  settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;editor.set_lod_build_settings(mesh,0,settings)
  E.set_metadata_tag(mesh,'Attribution','HK416 Full ReWorked by MojoLeeDa; Sketchfab 669a9ee17dc44580b53425a08c2f83d0; CC BY 4.0; AR interface adaptation for FPSGAME')
  save(mesh);receipt['meshes'][key]={'asset':mesh.get_path_name(),'saved':True,'materials':[s.material_interface.get_path_name() for s in slots]};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
for folder in ('','/FramedFirearms'):
 root='/Game/ColdSteelData/AttachmentIcons20260913'+folder
 for slot,part in [('stock','hk416_stock'),('reargrip','hk416_reargrip')]:
  name=slot+'_'+part;source=load(root+'/ue_hk416_'+slot+'_false')
  texture=A.duplicate_asset(name,root,source)
  if not texture:raise RuntimeError('Icon duplication failed '+name)
  save(texture);receipt['icons'][folder+'/'+name]={'asset':texture.get_path_name(),'saved':True};record()
receipt['status']='Four fitted static meshes and four icon textures imported/duplicated and saved';record()
print('416_AR_ASSETS_SAVED',len(receipt['meshes']),len(receipt['icons']))
