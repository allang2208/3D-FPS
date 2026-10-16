"""Read-only audit of every catalog user of tactical_telescopic."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];X=O/'Exports';X.mkdir(exist_ok=True)
old=json.loads((P/'SourceAssets/TelescopicStockSurface20261014/inputs.json').read_text())['assets']
r1=json.loads((P/'SourceAssets/TelescopicStockSurface20261014/install_receipt.json').read_text())['meshes']
accepted=json.loads((P/'SourceAssets/M16StockMaterialDiagnosis20261015/install_receipt.json').read_text())
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils
R={'assets':{},'materials':{},'textures':{},'read_only':True,'gameplay_tested':False}
if (O/'capture.json').exists():R=json.loads((O/'capture.json').read_text())
def record():(O/'capture.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(path):
 package=path.split('.')[0]
 if package.startswith('/Engine/'):return Path(r'E:\Program Files (x86)\UE_5.8\Engine\Content')/(package.removeprefix('/Engine/')+'.uasset')
 return P/'Content'/(package.removeprefix('/Game/')+'.uasset')
def texture(t):
 p=t.get_path_name()
 if p in R['textures']:return p
 v={'path':p,'sha256':hashlib.sha256(disk(p).read_bytes()).hexdigest()}
 for key in ('srgb','flip_green_channel','compression_settings','lod_group','lod_bias'):
  try:
   a=t.get_editor_property(key);v[key]=a if isinstance(a,(int,float,bool,str)) else str(a)
  except Exception:pass
 try:v['source_file']=t.get_editor_property('asset_import_data').get_first_filename()
 except Exception:pass
 R['textures'][p]=v;return p
def material(m):
 p=m.get_path_name()
 if p in R['materials']:return p
 base=m.get_base_material();v={'class':m.get_class().get_name(),'base':base.get_path_name(),'normal_samples':[],'normal_graph':[],'textures':{}}
 if isinstance(m,u.MaterialInstanceConstant):
  v['parent']=m.parent.get_path_name()
  v['scalars']={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(base)}
  for n in L.get_texture_parameter_names(base):
   t=L.get_material_instance_texture_parameter_value(m,n)
   if t:v['textures'][str(n)]=texture(t)
 seen=set()
 def walk(n):
  if not n or n.get_name() in seen:return
  seen.add(n.get_name());entry={'name':n.get_name(),'class':n.get_class().get_name()}
  if isinstance(n,u.MaterialExpressionTextureSample):
   t=n.get_editor_property('texture');param=None
   try:param=str(n.get_editor_property('parameter_name'))
   except Exception:pass
   if param and isinstance(m,u.MaterialInstanceConstant):t=L.get_material_instance_texture_parameter_value(m,param) or t
   entry.update(parameter=param,texture=texture(t) if t else None,sampler=str(n.get_editor_property('sampler_type')))
   if t:v['normal_samples'].append(entry.copy())
  if isinstance(n,u.MaterialExpressionTextureCoordinate):entry['uv']=n.get_editor_property('coordinate_index')
  if isinstance(n,u.MaterialExpressionCustom):entry['code']=n.get_editor_property('code')
  v['normal_graph'].append(entry)
  for parent in L.get_inputs_for_material_expression(base,n):walk(parent)
 root=L.get_material_property_input_node(base,u.MaterialProperty.MP_NORMAL)
 v['normal_root']=root.get_name() if root else None;walk(root)
 v['normal_uv_channels']=sorted({n['uv'] for n in v['normal_graph'] if 'uv' in n})
 R['materials'][p]=v;return p
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,source in old.items():
 if key in R['assets']:continue
 path=source['path'];mesh=u.load_asset(path)
 if not mesh:R['assets'][key]={'path':path,'missing':True};record();continue
 h=hashlib.sha256(disk(path).read_bytes()).hexdigest()
 row={'path':path,'sha256':h,'unchanged_since_R1':h==r1.get(key,{}).get('sha256'),'matches_accepted_M16':key=='M16' and h==accepted['installed']['sha256'],'slots':[]}
 for slot in mesh.static_materials:row['slots'].append({'name':str(slot.material_slot_name),'material':material(slot.material_interface) if slot.material_interface else None})
 lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
 mats,indices,names,status=G.get_section_material_list_from_static_mesh(mesh,lod)
 row['sections']=[{'slot_index':int(i),'slot_name':str(n),'material':m.get_path_name() if m else None} for m,i,n in zip(mats,indices,names)]
 settings=sms.get_lod_build_settings(mesh,0)
 row['build_settings']={k:settings.get_editor_property(k) for k in ('recompute_normals','recompute_tangents','use_full_precision_u_vs','use_high_precision_tangent_basis','remove_degenerates')}
 row['metadata']={k:E.get_metadata_tag(mesh,k) for k in ('M16StockSurfaceRecovery','M16StockRebuild','M16StockDonor','StockSurfaceRepair')}
 task=u.AssetExportTask();task.object=mesh;task.filename=str(X/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 row['exported']=u.Exporter.run_asset_export_task(task);row['export']=task.filename
 R['assets'][key]=row;record();print('STOCK_AUDIT_CAPTURE',key,'unchanged_R1',row['unchanged_since_R1'],flush=True)
# Read the shared failed bake and accepted private bake independently of reachability.
for path in ['/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Normal_Game',accepted['normal']['path']]:
 t=u.load_asset(path)
 if t:texture(t)
R['complete']=True;record();print('STOCK_AUDIT_CAPTURE_COMPLETE',len(R['assets']),flush=True)
