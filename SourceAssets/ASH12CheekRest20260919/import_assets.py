"""Save ASH cheek-rest geometry, PBR, wet variants and production card icon."""
import unreal as u
import json,shutil,os
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1];D='/Game/Weapons/ASH12/CheekRest20260919'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
receipt={'asset_directory':D,'materials':{},'tested':False,'option_id':'ash12_cheek_rest','exclusive_weapon':'ue_ash12'}
# Run in a complete editor because final StaticMesh build settings need it.
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
 raise RuntimeError('Stop PIE before importing and building this mesh.')

def load(path):
 asset=u.load_asset(path)
 if asset is None:raise RuntimeError('Missing '+path)
 return asset

def save(asset):
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Save failed '+asset.get_path_name())

def node(mat,cls,**props):
 n=L.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n

def wire(src,n,pin):
 a,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(a,out,n,pin):raise RuntimeError('Wire '+pin)

def output(src,prop):
 a,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output '+prop)

def custom(mat,code,inputs,size,label):
 n=node(mat,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)),description=label)
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n

def import_texture(file,kind,folder=None):
 task=u.AssetImportTask();task.filename=str(file);task.destination_name=Path(file).stem
 task.destination_path=folder or D+'/Textures';task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);t=load(task.destination_path+'/'+task.destination_name)
 t.srgb=kind in ('basecolor','icon')
 t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_MASKS if kind=='orm' else u.TextureCompressionSettings.TC_DEFAULT
 t.lod_group=u.TextureGroup.TEXTUREGROUP_UI if kind=='icon' else u.TextureGroup.TEXTUREGROUP_WEAPON
 if kind=='normal':t.flip_green_channel=False
 if kind=='icon':t.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 save(t);return t

textures={part:{k:import_texture(v,k) for k,v in files.items()} for part,files in auth['textures'].items()}
bead_code=(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(encoding='utf-8')

def material(part,wet=False):
 name='M_ASH12_Cheek_'+part+('_Wet' if wet else '')
 mat=u.load_asset(D+'/Materials/'+name)
 if mat:return mat
 mat=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 def sample(key,kind):return node(mat,u.MaterialExpressionTextureSample,texture=textures[part][key],sampler_type=kind)
 base=sample('basecolor',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 orm=sample('orm',u.MaterialSamplerType.SAMPLERTYPE_MASKS);normal=sample('normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 color=(base,'RGB');rough=(orm,'G');norm=(normal,'RGB')
 if wet:
  wetness=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
  beads=custom(mat,bead_code,{'UV':node(mat,u.MaterialExpressionTextureCoordinate),'Wet':wetness},4,'ASH cheek rest water beads')
  color=custom(mat,'return Base*(1-Data.a*.055);',{'Base':color,'Data':beads},3,'Wet film')
  rough=custom(mat,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1,'Wet roughness')
  norm=custom(mat,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':norm,'Data':beads},3,'Retain stipple underneath beads')
 output(color,'BASE_COLOR');output(rough,'ROUGHNESS');output(norm,'NORMAL')
 output((orm,'R'),'AMBIENT_OCCLUSION');output((orm,'B'),'METALLIC')
 output(node(mat,u.MaterialExpressionConstant,r=.5),'SPECULAR')
 E.set_metadata_tag(mat,'FinishReference','ASH12 Surface20260919 Upper metal; Lower polymer; original soft overmold')
 E.set_metadata_tag(mat,'TextureScale','UV0: 4 cm tile, dedicated BaseColor / ORM / DX normal')
 L.recompile_material(mat);save(mat);return mat

dry={part:material(part) for part in textures};wet={part:material(part,True) for part in textures}
for part in dry:receipt['materials'][part]={'dry':dry[part].get_path_name(),'wet':wet[part].get_path_name()}
task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=D;task.destination_name=auth['mesh']
task.automated=True;task.replace_existing=True;task.save=False
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_materials=False;options.import_textures=False;options.import_animations=False
data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
task.options=options;A.import_asset_tasks([task]);mesh=load(D+'/'+auth['mesh']);slots=mesh.static_materials
for i,s in enumerate(slots):
 part=str(s.material_slot_name).removeprefix('ASH12Cheek_');s.material_interface=dry[part];slots[i]=s
mesh.set_editor_property('static_materials',slots)
editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
settings.set_editor_property('recompute_normals',False);settings.set_editor_property('recompute_tangents',True);settings.set_editor_property('use_mikk_t_space',True)
editor.set_lod_build_settings(mesh,0,settings)
E.set_metadata_tag(mesh,'StockSurfaceSource',auth['source']);E.set_metadata_tag(mesh,'MountPivotRailCM',json.dumps(auth['runtime_pivot_cm']))
save(mesh)
receipt['mesh']={'path':mesh.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'source':auth['fbx']}
library=load('/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials')
mapping=dict(library.get_editor_property('wet_materials'))
for part,w in wet.items():mapping[dry[part].get_path_name()]=w
library.set_editor_property('wet_materials',mapping);save(library);receipt['weather_library']=library.get_path_name()
png=Path(auth['icon']);dest=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/png.name
shutil.copy2(png,dest);icon=import_texture(png,'icon','/Game/ColdSteelData/AttachmentIcons20260913')
receipt['icon']={'png':str(dest),'texture':icon.get_path_name()}
(O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ASH12_CHEEK_REST_IMPORTED')
if os.environ.get('ASH_CHEEK_OWNED_EDITOR')=='1':u.SystemLibrary.quit_editor()
