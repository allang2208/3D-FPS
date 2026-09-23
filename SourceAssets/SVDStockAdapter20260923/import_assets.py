"""Install the split stock mesh and four SVD rod/stock assemblies without gameplay."""
import unreal as u,json,ast,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent;P='/Game/Weapons/SVDDragunov20260922/StockAdapter20260923'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
geo=json.loads((O/'authoring.json').read_text())
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {'materials':{},'meshes':{},'wet_materials':{},'game_tested':False}
tablepath='/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active: preserve state')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(P) or p==tablepath for p in dirty):raise RuntimeError('Unsaved stock target assets')
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(a):
 if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+str(a))
def clone(original,path):
 a=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(original.get_path_name(),path)
 if not a:raise RuntimeError('Duplicate failed '+path)
 return a
def functions(path,names):
 tree=ast.parse(path.read_text(encoding='utf-8-sig'))
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(path),'exec'),globals())
functions(S/'SVDAttachments20260923/import_assets.py',['node','link','output','const','previous','custom','graphcopy','coating','addwet'])
def finish(m,result):
 L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compile failed '+m.get_path_name()+str(errors))
 save(m)
 if result!=m:L.update_material_instance(result);save(result)
def vertex(m,cls):
 n=node(m,u.MaterialExpressionVertexInterpolator);link(node(m,cls),n,'VS');return n
coatbc=u.load_asset('/Game/Weapons/SVDDragunov20260922/Accessories20260923/Textures/T_SVD_AttachmentCoat_BaseColor')
coato=u.load_asset('/Game/Weapons/SVDDragunov20260922/Accessories20260923/Textures/T_SVD_AttachmentCoat_ORM')
beads=(S/'WeatherNatural20260912/WeaponBeads.hlsl').read_text().replace('return float4(slope,beads,saturate(Wet));','float coverage=saturate(Wet*20.0); return float4(slope*coverage,beads*coverage,saturate(Wet));')
matte=json.loads((S/'SVDMatteDetail20260923/finish_receipt.json').read_text())
steelinfo=matte['materials']['/Game/Weapons/SVDDragunov20260922/Accessories20260923/Materials/M_SVD_InterfaceSteel.M_SVD_InterfaceSteel']
steel=u.load_asset(steelinfo['dry']);poly=u.load_asset('/Game/Weapons/ReferenceStock5080/Refined/M_StockPolymer')
if not steel or not poly or not coatbc or not coato:raise RuntimeError('Missing current SVD stock finish sources')
wetmap={steel.get_path_name():u.load_asset(steelinfo['wet'])}
addwet(poly)

def stock_material(label,info):
 if info['source']=='SVD_CURRENT_MATTE_STEEL':return steel
 original=u.load_asset(info['source']);tag=info['source_slot'].lower()
 if not original:raise RuntimeError('Missing donor material '+info['source'])
 if any(k in tag for k in ['polymer','rubber']):addwet(original);return original
 path=P+'/Materials/M_'+label
 if path in receipt['materials']:
  result=u.load_asset(path);addwet(result);return result
 m,result=graphcopy(original,path);values=coating(m)
 # Preserve mixed polymer regions, original structural normal, AO and markings.
 mixed='corestockbody' in tag
 mask=custom(m,'return smoothstep(.2,.65,Metal);',{'Metal':previous(m,'METALLIC',.84)},1,'Preserve stock polymer') if mixed else const(m,1.)
 detail=custom(m,(S/'SVDMatteDetail20260923/MicroFinish.hlsl').read_text(),
  {'P':vertex(m,u.MaterialExpressionPreSkinnedPosition),'N':vertex(m,u.MaterialExpressionPreSkinnedNormal)},4,'SVD stock physical micro finish')
 strength=node(m,u.MaterialExpressionScalarParameter,parameter_name='SVD_MicroScratchStrength',default_value=.30)
 for prop,program,size in [('BASE_COLOR','MatteColor.hlsl',3),('ROUGHNESS','MatteRoughness.hlsl',1)]:
  values[prop]=custom(m,(S/'SVDMatteDetail20260923'/program).read_text(),
   {'Base':values[prop],'Detail':detail,'Strength':strength,'Region':const(m,1.)},size,'SVD stock matte '+prop)
 for prop,value in values.items():
  if mixed:
   blend=node(m,u.MaterialExpressionLinearInterpolate);link(previous(m,prop,(.023,.027,.03) if prop=='BASE_COLOR' else .5),blend,'A');link(value,blend,'B');link(mask,blend,'Alpha');value=blend
  output(m,value,prop)
 E.set_metadata_tag(m,'WeaponFinishReference','SVD current receiver / MatteDetail20260923')
 E.set_metadata_tag(m,'WeaponFinishUV','UV0 donor normal/AO retained; UV2 physical SVD coating 5 cm')
 finish(m,result);receipt['materials'][path]={'source':original.get_path_name(),'saved':True};record();addwet(result);return result

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in geo['meshes'].items():
  if key in receipt['meshes']:continue
  bindings={label:stock_material(label,m) for label,m in info['materials'].items()}
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
  d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  path=P+'/Meshes/'+info['name']
  if E.does_asset_exist(path):raise RuntimeError('Unrecorded stock asset exists: '+path)
  t=u.AssetImportTask();t.filename=str(O/'Exports'/(info['name']+'.fbx'));t.destination_path=P+'/Meshes';t.destination_name=info['name'];t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(path)
  if not mesh or not t.imported_object_paths:raise RuntimeError('Stock mesh import failed '+key)
  slots=mesh.get_editor_property('static_materials')
  for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
  mesh.set_editor_property('static_materials',slots);save(mesh)
  receipt['meshes'][key]={'asset':path,'source':t.filename,'saved':True,'size_cm':[v*2 for v in mesh.get_bounds().box_extent.to_tuple()],
   'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}};record();print('SVD_STOCK_SAVED',key,flush=True)
 if 'viewmodel' not in receipt['meshes']:
  old=u.load_asset('/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular')
  bindings={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('materials')}
  bindings['SVD_FactoryStock']=bindings['SM_SVD_Body_001'];bindings['SVD_StockCutPolymer']=poly
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opts.import_as_skeletal=True
  opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=old.skeleton
  d=opts.skeletal_mesh_import_data
  d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  path=P+'/SK_SVD_ModularStock'
  if E.does_asset_exist(path):raise RuntimeError('Unrecorded SVD viewmodel exists')
  t=u.AssetImportTask();t.filename=str(O/'Exports/SK_SVD_ModularStock.fbx');t.destination_path=P;t.destination_name='SK_SVD_ModularStock';t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(path)
  if not mesh or not t.imported_object_paths:raise RuntimeError('SVD split mesh import failed')
  slots=mesh.get_editor_property('materials')
  for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
  mesh.set_editor_property('materials',slots)
  for prop in ['physics_asset','post_process_anim_blueprint','positive_bounds_extension','negative_bounds_extension']:
   mesh.set_editor_property(prop,old.get_editor_property(prop))
  save(mesh);receipt['meshes']['viewmodel']={'asset':path,'saved':True,'skeleton':mesh.skeleton.get_path_name(),
   'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
table=u.load_asset(tablepath);disk=Path(u.Paths.project_dir())/'Content'/Path(tablepath.removeprefix('/Game/')).with_suffix('.uasset')
backup=O/'Before/DA_SVD_AttachmentWetMaterials.uasset';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(disk,backup)
mapping=dict(table.get_editor_property('wet_materials'));mapping.update(wetmap)
for dry,path in receipt['wet_materials'].items():mapping[dry]=u.load_asset(path)
table.set_editor_property('wet_materials',mapping);save(table)
receipt['wet_table']={'asset':tablepath,'saved':True};record()
for key,info in json.loads((O/'icons.json').read_text()).items():
 if key in receipt.setdefault('icons',{}):continue
 t=u.AssetImportTask();t.filename=info['output'];t.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';t.destination_name=key;t.automated=True;t.save=False
 A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+key)
 if not tex or not t.imported_object_paths:raise RuntimeError('Stock icon import failed '+key)
 tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 save(tex);receipt['icons'][key]={'asset':tex.get_path_name(),'saved':True};record()
receipt['status']='imported_and_saved';record()
print('SVD_STOCK_IMPORT_COMPLETE',len(receipt['meshes']),flush=True)
