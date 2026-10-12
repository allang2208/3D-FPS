"""Author/save fitted grips and a factory-only material section; no runtime tests."""
import unreal as u,json,hashlib,shutil,math
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/Super90/RearGrips20261012'
C=json.loads((O/'inputs.json').read_text());M=json.loads((O/'models.json').read_text());T=json.loads((O/'material_sources.json').read_text())
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
RP=O/'install_receipt.json';R=json.loads(RP.read_text()) if RP.exists() else {'saved':[],'meshes':{},'materials':{},'complete':False,'runtime_tested':False};R['complete']=False
def record():RP.write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def disk(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
 record();return a
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE to save rear grips')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
native_path=C['assets']['super90']['path'];mesh=load(native_path)
if native_path in dirty:raise RuntimeError('Native mesh has unsaved edits')
if E.get_metadata_tag(mesh,'Super90RearGripSection')!='20261012':
 if sha(native_path)!=C['assets']['super90']['sha256']:raise RuntimeError('Native mesh changed since source extraction')

master_path=D+'/Materials/M_Super90RearGripSurface'
master=load(master_path) if E.does_asset_exist(master_path) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',master_path)
def node(cls,**props):
 n=L.create_material_expression(master,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(source,dest,pin,out=''):
 if not L.connect_material_expressions(source,out,dest,pin):raise RuntimeError('Material connection '+pin)
def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value,group='Super90 finish')
if E.get_metadata_tag(master,'Super90RearGripGraph')!='20261012':
 expressions=L.get_material_expressions(master)
 params={str(n.get_editor_property('parameter_name')):n for n in expressions if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter))}
 customs={str(n.get_editor_property('description')):n for n in expressions if isinstance(n,u.MaterialExpressionCustom)}
 vertex=node(u.MaterialExpressionVertexColor);use=scalar('UseVertexMetalMask',0)
 mask=node(u.MaterialExpressionLinearInterpolate,const_a=1);wire(vertex,mask,'B','R');wire(use,mask,'Alpha')
 polycolor=node(u.MaterialExpressionVectorParameter,parameter_name='PolymerColor',default_value=u.LinearColor(.019,.019,.018,1),group='Super90 finish')
 for key,poly,target,pin in [('FinishColor',polycolor,'WS_ColorRough','Finish'),('Roughness',scalar('PolymerRoughness',.55),'WS_ColorRough','Rough')]:
  blend=node(u.MaterialExpressionLinearInterpolate);wire(poly,blend,'A','RGB' if key=='FinishColor' else '');wire(params[key],blend,'B','RGB' if key=='FinishColor' else '');wire(mask,blend,'Alpha');wire(blend,customs[target],pin)
 for key,pin in [('Metallic','Metal'),('EdgeMetallic','EdgeMetal')]:
  blend=node(u.MaterialExpressionMultiply);wire(params[key],blend,'A');wire(mask,blend,'B');wire(blend,customs['WS_MetalAO'],pin)
 # Source grips have geometric relief and a packed roughness map; do not apply the gun atlas to their UVs.
 tex=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='DonorSurface',texture=load(T['phantom_reargrip']['textures'][1]['path']),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,group='Source')
 rough=node(u.MaterialExpressionLinearInterpolate,const_a=.5);wire(tex,rough,'B','G');wire(scalar('UseDonorRoughness',0),rough,'Alpha');wire(rough,customs['WS_ColorRough'],'SrcR')
 master.set_editor_property('automatically_set_usage_in_editor',False)
 for prop in ('used_with_skeletal_mesh','used_with_clothing','used_with_morph_targets'):master.set_editor_property(prop,False)
 E.set_metadata_tag(master,'Super90RearGripGraph','20261012');L.recompile_material(master);save(master)
native_material=C['assets']['super90']['slots'][10]['material'];native_params=C['materials'][native_material]
def instance(name,scalars={},vectors={},textures={},copy_native=False):
 p=D+'/Materials/MI_'+name
 mat=load(p) if E.does_asset_exist(p) else A.create_asset('MI_'+name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 L.set_material_instance_parent(mat,master)
 if copy_native:
  for n,v in native_params['scalars'].items():L.set_material_instance_scalar_parameter_value(mat,n,v)
  for n,v in native_params['vectors'].items():L.set_material_instance_vector_parameter_value(mat,n,u.LinearColor(*v))
  for n,v in native_params['textures'].items():
   if v:L.set_material_instance_texture_parameter_value(mat,n,load(v))
 else:
  values={'Metallic':0,'Roughness':.55,'GrainTileCm':2,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0,'SourceColorWeight':0,'SourceRoughnessWeight':0,'EdgeWear':0,'ScratchAmount':0,'Stipple':0,'HandlingPolish':0,'CavityDarken':0,'CavityRoughness':0,'WeaponWetness':0,'MaskUVChannel':0}
  for n,v in values.items():L.set_material_instance_scalar_parameter_value(mat,n,v)
  L.set_material_instance_vector_parameter_value(mat,'FinishColor',u.LinearColor(.019,.019,.018,1))
 for n,v in scalars.items():L.set_material_instance_scalar_parameter_value(mat,n,v)
 for n,v in vectors.items():L.set_material_instance_vector_parameter_value(mat,n,u.LinearColor(*v,1))
 for n,v in textures.items():L.set_material_instance_texture_parameter_value(mat,n,load(v))
 L.update_material_instance(mat);save(mat);R['materials'][name]=mat.get_path_name();record();return mat
native_mi=instance('S90_RearGrip_NativeInterface',{'UseVertexMetalMask':0,'UseDonorRoughness':0},copy_native=True)
transition=instance('S90_RearGrip_Transition',{'BeadScale':10,'UseVertexMetalMask':0})
materials={}
for key,row in M['parts'].items():
 packed=next(t['path'] for t in T[key]['textures'] if 'MetalRough' in t['path'])
 area,uvarea=row['area_cm2_uv']['0'];stable=key=='stable_antislip_reargrip'
 materials[key]=instance('S90_'+key,{'UseVertexMetalMask':0 if stable else 1,'Metallic':0 if stable else 1,'Roughness':.62 if stable else .46,'PolymerRoughness':.55,'UseDonorRoughness':1,'SourceRoughnessWeight':.025,'BeadScale':math.sqrt(area/uvarea)/.42}, {'FinishColor':[.0103]*3 if stable else [.020,.021,.022]}, {'DonorSurface':packed})
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,row in M['parts'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;imp.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Meshes';task.destination_name='SM_Super90_'+key;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
  A.import_asset_tasks([task]);part=load(D+'/Meshes/'+task.destination_name);slots=list(part.static_materials)
  binds={'S90_CommonBody':materials[key],'S90_NativeInterface':native_mi,'S90_TransitionPolymer':transition}
  for i,s in enumerate(slots):s.material_interface=binds[str(s.material_slot_name)];slots[i]=s
  part.set_editor_property('static_materials',slots);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(part)
  ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);settings=ed.get_lod_build_settings(part,0)
  settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True;ed.set_lod_build_settings(part,0,settings)
  E.set_metadata_tag(part,'Super90RearGripSource',C['assets'][key]['path']+'; native upper web + continuous neck; component bind cm; original UV and colors')
  save(part);R['meshes'][key]=part.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
if E.get_metadata_tag(mesh,'Super90RearGripSection')!='20261012':
 backup=O/'Before/SK_Super90_V7.uasset';backup.parent.mkdir(exist_ok=True)
 if not backup.exists():shutil.copy2(disk(native_path),backup)
 slots=[s.copy() for s in mesh.materials];factory=slots[10].copy();factory.material_slot_name='S90_FactoryRearGrip';slots.append(factory)
 G=u.GeometryScript_AssetUtils;dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source geometry')
 ids=json.loads((O/'factory_triangles.json').read_text())
 for i in ids:
  if u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]!=10:raise RuntimeError('Changed factory grip source section')
  u.GeometryScript_Materials.set_triangle_material_id(dm,i,len(slots)-1)
 names=[s.get_editor_property('imported_material_slot_name') for s in slots[:-1]]+['S90_FactoryRearGrip']
 opt=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True,replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=names,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opt,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write source material groups')
 # GeometryScript creates the read-only imported name for the appended slot.
 slots[-1]=mesh.materials[-1].copy();slots[-1].material_slot_name='S90_FactoryRearGrip';slots[-1].material_interface=factory.material_interface
 mesh.set_editor_property('materials',slots);E.set_metadata_tag(mesh,'Super90RearGripSection','20261012');save(mesh)
 R['factory_section']={'faces':len(ids),'before_sha256':C['assets']['super90']['sha256'],'saved_sha256':sha(native_path),'positions_uv_weights_animations_edited':False}
icon_name='ue_super90_reargrip_false';icon_dir=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms';shutil.copy2(O/(icon_name+'.png'),icon_dir/(icon_name+'.png'))
task=u.AssetImportTask();task.filename=str(icon_dir/(icon_name+'.png'));task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms';task.destination_name=icon_name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
icon=load(task.destination_path+'/'+icon_name);icon.srgb=True;icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI;icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.never_stream=True;icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(icon)
R['icon']=icon.get_path_name();R['complete']=True;record();print('SUPER90_REARGRIPS_SAVED',json.dumps(R))
