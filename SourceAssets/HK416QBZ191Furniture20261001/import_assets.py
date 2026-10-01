"""Save two QBZ-specific 416 meshes and receiver-matched metallic finishes."""
import unreal as u,json,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];H='/Game/Weapons/HK416/Reworked20260930';D='/Game/Weapons/HK416/ARParts20261001/QBZ191'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=P.resolve():raise RuntimeError('Wrong project for QBZ furniture publication')
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
models=json.loads((O/'models.json').read_text(encoding='utf-8'));receipt={'meshes':{},'materials':{},'testing':'Not run'}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
 asset=u.load_asset(path)
 if not asset:raise RuntimeError('Missing source '+path)
 return asset
def save(asset):
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Save failed '+asset.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,n,pin):
 a,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(a,out,n,pin):raise RuntimeError('Material pin '+pin)
def output(src,prop):
 a,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def sample(m,path,uv,kind='masks'):
 t=load(path);sampler={'color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'masks':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
 n=node(m,u.MaterialExpressionTextureSample,texture=t,sampler_type=sampler);wire(uv,n,'UVs');return n
def custom(m,code,inputs,size):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for key in inputs:
  pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
 n.set_editor_property('inputs',pins)
 for key,value in inputs.items():wire(value,n,key)
 return n
def blend(m,a,b,mask):
 n=node(m,u.MaterialExpressionLinearInterpolate);wire(a,n,'A');wire(b,n,'B');wire(mask,n,'Alpha');return n
coatroot='/Game/Weapons/TacticalTelescopicStock20260914/QBZ191/Textures/T_QBZ191_StableCollar_'
materials={}
for slot,group in [('M_HK416_Stock','Stock'),('M_HK416_Lower_body','Lower_Body')]:
 name='M_QBZ191_416_'+group;path=D+'/Materials/'+name
 m=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 for old in list(L.get_material_expressions(m)):L.delete_material_expression(m,old)
 uv0=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0);uv1=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
 root=H+'/Textures/T_HK416_'+group+'_'
 base=sample(m,root+'albedo',uv0,'color');rough=sample(m,root+'roughness',uv0);metal=sample(m,root+'metallic',uv0);normal=sample(m,root+'normal',uv0,'normal');ao=sample(m,root+'AO',uv0)
 coat=sample(m,coatroot+'BaseColor',uv1,'color');orm=sample(m,coatroot+'ORM',uv1)
 mask=custom(m,'return smoothstep(.25,.65,Metal);',{'Metal':(metal,'R')},1)
 b=blend(m,(base,'RGB'),(coat,'RGB'),mask);r=blend(m,(rough,'R'),(orm,'G'),mask)
 output(blend(m,(metal,'R'),(orm,'B'),mask),'METALLIC');output((ao,'R'),'AMBIENT_OCCLUSION')
 wet=node(m,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
 beads=custom(m,(P/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),{'UV':uv0,'Wet':wet},4)
 output(custom(m,'return Base*(1-Data.a*.07);',{'Base':b,'Data':beads},3),'BASE_COLOR')
 output(custom(m,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':r,'Data':beads},1),'ROUGHNESS')
 output(custom(m,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',{'Base':(normal,'RGB'),'Data':beads},3),'NORMAL')
 m.set_editor_property('used_with_skeletal_mesh',False);m.set_editor_property('automatically_set_usage_in_editor',False)
 E.set_metadata_tag(m,'ReceiverFinish','QBZ191 accepted receiver coating, UV1 10cm; native 416 polymer, normal and AO on UV0')
 L.recompile_material(m);save(m);materials[slot]=m;receipt['materials'][slot]=m.get_path_name();record()
materials['QBZ416_AdapterMetal']=load('/Game/Weapons/TacticalTelescopicStock20260914/QBZ191/M_TacticalStock_Adapter_QBZ191')
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,part in models['parts'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task=u.AssetImportTask();task.filename=part['fbx'];task.destination_path=D;task.destination_name=part['name'];task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
  A.import_asset_tasks([task]);mesh=load(D+'/'+part['name']);slots=list(mesh.static_materials)
  for i,slot in enumerate(slots):slot.material_interface=materials[re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;editor.set_lod_build_settings(mesh,0,settings)
  E.set_metadata_tag(mesh,'Attribution','HK416 Full ReWorked by MojoLeeDa, Sketchfab 669a9ee17dc44580b53425a08c2f83d0, CC BY 4.0; QBZ receiver adaptation for FPSGAME')
  save(mesh);receipt['meshes'][key]={'asset':mesh.get_path_name(),'saved':True};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
library=load(H+'/DA_HK416_WetMaterials');entries=dict(library.get_editor_property('wet_materials'))
for key in ('M_HK416_Stock','M_HK416_Lower_body'):entries[materials[key].get_path_name()]=materials[key]
library.set_editor_property('wet_materials',entries);save(library)
receipt['status']='Two QBZ191 fitted meshes, two receiver finish materials and wet mappings saved';record();print('416_QBZ_ASSETS_SAVED',len(receipt['meshes']))
