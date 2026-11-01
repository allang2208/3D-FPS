"""Publish only M24 continuity meshes and private finishes; preserve all poses."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/StockContinuity20261031';MD=D+'/Materials'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
spec=json.loads((O/'geometry_contract.json').read_text());inputs=json.loads((O/'inputs.json').read_text())
R={'complete':False,'saved':[],'materials':{},'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def disk(p):return Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
 if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
 record();return a
def clone(src,name):
 p=MD+'/'+name
 return load(p) if E.does_asset_exist(p) else E.duplicate_asset(src,p)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for row in inputs['assets'].values():
 if row['path'] in dirty:raise RuntimeError('Unsaved target retained '+row['path'])
 if hashlib.sha256(disk(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent mesh edit retained '+row['path'])
 dest=O/'Before'/(row['path'].removeprefix('/Game/')+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(disk(row['path']),dest)
def scalar(m,values):
 for k,v in values.items():L.set_material_instance_scalar_parameter_value(m,k,v)
def vector(m,k,v):L.set_material_instance_vector_parameter_value(m,k,u.LinearColor(*v,1))
def normal_strength(master,value):
 old=L.get_material_property_input_node(master,u.MaterialProperty.MP_NORMAL);out=L.get_material_property_input_node_output_name(master,u.MaterialProperty.MP_NORMAL)
 n=L.create_material_expression(master,u.MaterialExpressionCustom);n.set_editor_property('description','M24 restrained source normals');n.set_editor_property('code','return normalize(float3(N.xy*Strength,N.z));');n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
 ins=[]
 for name in ('N','Strength'):
  x=u.CustomInput();x.set_editor_property('input_name',name);ins.append(x)
 n.set_editor_property('inputs',ins)
 p=L.create_material_expression(master,u.MaterialExpressionScalarParameter);p.set_editor_property('parameter_name','ContinuityNormalStrength');p.set_editor_property('default_value',value)
 L.connect_material_expressions(old,out,n,'N');L.connect_material_expressions(p,'',n,'Strength');L.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
def compile_master(m):
 result=L.recompile_material(m)
 if isinstance(result,(list,tuple)) and result:raise RuntimeError(str(result))
 save(m);return m
masters={}
def master(source,label,strength):
 if label in masters:return masters[label]
 m=clone(source,label)
 if E.get_metadata_tag(m,'M24Continuity')!='20261031':
  normal_strength(m,strength);E.set_metadata_tag(m,'M24Continuity','20261031')
 masters[label]=m;return m
common={'SourceRoughnessWeight':.10,'SourceRoughnessPivot':.5,'EdgeWear':0,'EdgeHighlight':.015,'ScratchAmount':0,'HandlingPolish':0,'GrainRoughness':.006,'MottleRoughness':.002,'MottleColor':0,'Stipple':0,'WeaponWetness':0}
materials={}
for slot,source in spec['materials'].items():
 m=clone(source,'MI_'+slot);parent=load(source).get_editor_property('parent')
 if slot.startswith('M24_Grip_'):
  scalar(m,{'R01_Roughness':.48,'R01_SourceRoughnessWeight':.08,'R01_PolymerRoughness':.59,'R01_PolymerSourceWeight':.06,'R01_Grain':.004,'R01_Variation':.001,'R02_SourceColorContrast':.3})
  vector(m,'R01_PolymerTint',(.018,.020,.021));vector(m,'R01_ToneScale',(.43,.46,.49))
 else:
  label='M_M24StockSurface' if slot=='SniperStock_MeshySurface' else 'M_M24GripSurface' if slot=='M24_NewPistolGrip' else 'M_M24MetalSurface'
  parent=master(parent.get_path_name(),label,.65 if 'Stock' in label else .45 if 'Metal' in label else .8)
  L.set_material_instance_parent(m,parent);scalar(m,common)
  ispoly=slot=='M24_NewPistolGrip' or slot=='M24_Advanced_1'
  scalar(m,{'SourceColorWeight':0,'Roughness':.59 if ispoly else .48,'Metallic':0 if ispoly else 1})
  vector(m,'FinishColor',(.018,.020,.021) if ispoly else (.026,.029,.032))
  if slot=='M24_NewReceiverMetal':scalar(m,{'MaskUVChannel':0,'EdgeHighlight':0,'AOStrength':0,'CavityDarken':0,'CavityRoughness':0})
  if slot=='SniperStock_MeshySurface':
   # Keep Meshy's material-identity and original label/texture detail, compress
   # broad source colour and roughness so it matches the receiver finish.
   scalar(m,{'SourceColorWeight':.15,'SourceRoughnessWeight':.10,'AOStrength':.35})
 L.update_material_instance(m);save(m);materials[slot]=m;R['materials'][slot]=m.get_path_name()
for m in masters.values():compile_master(m)
# Regional body/scope masters remain private to M24; shared WS/M4/SVD assets are untouched.
regional={}
for key in ('host','scope'):
 mesh=load(inputs['assets'][key]['path']);slots=list(mesh.materials if key=='host' else mesh.static_materials)
 for i,slot in enumerate(slots):
  src=slot.material_interface
  if not src or src.get_path_name() not in inputs['materials']:continue
  par=src.get_editor_property('parent') if isinstance(src,u.MaterialInstanceConstant) else None
  if not par or 'M_M24RegionalSurface' not in par.get_name():continue
  label='M_M24Regional_'+key;pm=master(par.get_path_name(),label,.75)
  for node in L.get_material_expressions(pm):
   if not isinstance(node,u.MaterialExpressionCustom):continue
   desc=str(node.get_editor_property('description'))
   if desc=='M24_SourceMarkings':node.set_editor_property('code','float ink=smoothstep(.62,.85,min(Src.r,min(Src.g,Src.b))); return saturate(max(max(BaseWeight,ink*.35),Region.b));')
   if desc=='M24_RegionFinish':node.set_editor_property('code','float rubber=smoothstep(.64,.70,Region.g); float3 dielectric=lerp(Poly,float3(.011,.012,.013),rubber); return float4(lerp(dielectric,MetalColor,Metal),lerp(max(Region.g,.59),max(Region.r,.48),Metal));')
  mi=clone(src.get_path_name(),'MI_M24_Regional_'+key);L.set_material_instance_parent(mi,pm);scalar(mi,common);scalar(mi,{'SourceColorWeight':.04,'SourceRoughnessWeight':.06});vector(mi,'FinishColor',(.026,.029,.032));vector(mi,'PolymerColor',(.018,.020,.021));L.update_material_instance(mi);save(mi)
  slot.material_interface=mi;slots[i]=slot;regional[key]=mi.get_path_name()
 mesh.set_editor_property('materials' if key=='host' else 'static_materials',slots);save(mesh)
for label,m in masters.items():
 if label.startswith('M_M24Regional_'):compile_master(m)
R['regional']=regional
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for name,file in spec['exports'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=file;task.destination_path=inputs['assets'][name]['path'].rsplit('/',1)[0];task.destination_name=name;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);mesh=load(task.destination_path+'/'+name)
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
  sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
  bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
  u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
  lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False;lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))];sub.set_lods(mesh,lod)
  if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Tangent authoring failed '+name)
  E.set_metadata_tag(mesh,'Source',str(O/'M24_StockContinuity_Editable.blend'));save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
R['complete']=True;record();print('M24_CONTINUITY_SAVED',len(R['saved']),flush=True)
