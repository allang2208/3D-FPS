"""Install one two-sample fabric master and three garment instances in the editor."""
import unreal as u,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from fabric09_settings import *
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=ROOT.parent.parent/'FPSGAME.uproject':
 raise RuntimeError('Connected editor is not FPSGAME')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; material installation deferred')
mesh_path=DEST+'/SK_WitchRebuilt';master_path=DEST+'/Materials/M_WitchRebuilt_Fabric09'
targets={mesh_path,master_path}|{DEST+'/Materials/'+p[1] for p in PARTS.values()}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&targets:raise RuntimeError('Unsaved target assets retained: '+str(sorted(dirty&targets)))
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
settings=json.loads((OUT/'fabric09_parameters.json').read_text(encoding='utf-8'))
mesh=u.load_asset(mesh_path)
if not mesh:raise RuntimeError('WitchRebuilt mesh missing')
slots=list(mesh.materials);before=OUT/'Before/material_assignments.json';before.parent.mkdir(parents=True,exist_ok=True)
if not before.exists():
 before.write_text(json.dumps([{'slot':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots],indent=2),encoding='utf-8')
revision='Fabric09: shared opaque weave, two UV0 texture samples'
master=u.load_asset(master_path) if L.does_asset_exist(master_path) else None
def save(asset):
 if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
if master and L.get_metadata_tag(master,'WitchSurfaceRevision')!=revision:
 raise RuntimeError('Fabric09 master exists without completion marker; preserve graph and resume authoring explicitly')
if not master:
 master=AT.create_asset('M_WitchRebuilt_Fabric09',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 for key in ('two_sided','used_with_skeletal_mesh','used_with_clothing'):master.set_editor_property(key,True)
 master.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
 def node(cls):return M.create_material_expression(master,cls)
 def link(a,b,p,output=''):
  if not M.connect_material_expressions(a,output,b,p):raise RuntimeError('Fabric09 material connection failed: '+b.get_name()+'.'+p)
 def con(v):
  n=node(u.MaterialExpressionConstant);n.set_editor_property('r',float(v));return n
 def scalar(name,default):
  n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',float(default));return n
 def vector(name,value):
  n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1.));return n
 def binary(cls,a,b,aout='',bout=''):
  n=node(cls);link(a,n,'A',aout);link(b,n,'B',bout);return n
 uv=node(u.MaterialExpressionTextureCoordinate);uv.coordinate_index=0
 vertex=node(u.MaterialExpressionVertexColor)
 repeats=node(u.MaterialExpressionLinearInterpolate)
 link(scalar('WeaveTiling',149.15),repeats,'A');link(scalar('RepairWeaveTiling',14.5376),repeats,'B');link(vertex,repeats,'Alpha','A')
 coords=binary(u.MaterialExpressionMultiply,uv,repeats)
 samples=[]
 for suffix,kind in (('N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('R',u.MaterialSamplerType.SAMPLERTYPE_MASKS)):
  n=node(u.MaterialExpressionTextureSample);n.texture=u.load_asset(DEST+'/Textures/Detail/T_Witch_FabricDetail_'+suffix)
  if not n.texture:raise RuntimeError('Required retained weave texture missing: '+suffix)
  n.set_editor_property('sampler_type',kind);link(coords,n,'Coordinates');samples.append(n)
 normal_tex,rough_tex=samples
 deviation=binary(u.MaterialExpressionSubtract,rough_tex,con(.75),'R')
 variation=binary(u.MaterialExpressionAdd,con(1.),binary(u.MaterialExpressionMultiply,deviation,scalar('ColorDetail',COLOR_DETAIL)))
 color=binary(u.MaterialExpressionMultiply,vector('ClothColor',COLOR),variation)
 rough=binary(u.MaterialExpressionAdd,scalar('Roughness',ROUGHNESS),binary(u.MaterialExpressionMultiply,deviation,scalar('RoughnessDetail',ROUGHNESS_DETAIL)))
 clamp=node(u.MaterialExpressionClamp);clamp.set_editor_property('min_default',.72);clamp.set_editor_property('max_default',.96);link(rough,clamp,M.get_material_expression_input_names(clamp)[0])
 normal=node(u.MaterialExpressionCustom);normal.set_editor_property('code','return normalize(float3(N.xy*Strength,max(N.z,0.85)));')
 normal.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
 entries=[]
 for name in ('N','Strength'):
  entry=u.CustomInput();entry.set_editor_property('input_name',name);entries.append(entry)
 normal.set_editor_property('inputs',entries);link(normal_tex,normal,'N','RGB');link(scalar('NormalStrength',NORMAL_STRENGTH),normal,'Strength')
 slab=node(u.MaterialExpressionSubstrateShadingModels)
 for expr,prop,pin in ((color,u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(normal,u.MaterialProperty.MP_NORMAL,'Normal'),(clamp,u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(scalar('Specular',SPECULAR),u.MaterialProperty.MP_SPECULAR,'Specular'),(con(0),u.MaterialProperty.MP_METALLIC,'Metallic')):
  M.connect_material_property(expr,'',prop);link(expr,slab,pin)
 M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 errors=M.recompile_material(master)
 if errors:raise RuntimeError('Fabric09 material compilation failed: '+str(errors))
 L.set_metadata_tag(master,'WitchSurfaceRevision',revision);save(master)
instances={}
for part,(_,name,_) in PARTS.items():
 path=DEST+'/Materials/'+name
 instance=u.load_asset(path) if L.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 M.set_material_instance_parent(instance,master)
 for key,value in settings[part].items():
  if key=='ClothColor':M.set_material_instance_vector_parameter_value(instance,key,u.LinearColor(*value,1.))
  else:M.set_material_instance_scalar_parameter_value(instance,key,float(value))
 M.update_material_instance(instance);L.set_metadata_tag(instance,'WitchSurfaceRevision',revision);save(instance);instances[part]=instance
assignments=[]
for slot in slots:
 name=str(slot.get_editor_property('imported_material_slot_name'))
 part=next((p for p in PARTS if p in name),None)
 if part:
  slot.material_interface=instances[part];assignments.append({'slot':name,'material':instances[part].get_path_name()})
mesh.set_editor_property('materials',slots)
L.set_metadata_tag(mesh,'Surface','Fabric09: upper, cuffs, waist, skirt and lining share the same opaque weave; Seams07 geometry and Drape07 retained')
save(mesh)
result={'revision':'Fabric09','master':master.get_path_name(),'assignments':assignments,'parameters':settings,
 'texture_samples_per_fabric_pixel':2,'new_texture_assets':0,'new_material_slots':0,
 'geometry_animation_cloth_solver_changed':False,'runtime_tested':False,'performance_measured':False,'user_visual_acceptance':False}
(OUT/'ue_asset_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
p=ROOT/'ue_delivery.json';delivery=json.loads(p.read_text(encoding='utf-8'));delivery.update(status='Fabric09 shared cloth installed; user visual and performance acceptance pending',revision09=result)
p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result))
