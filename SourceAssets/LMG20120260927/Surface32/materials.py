"""201-private low-glare coating; retain the original UV0 structure normal."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/Surface32';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; save deferred')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(m,cls,**props):
 n=M.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,p):
 n,ch=a if isinstance(a,tuple) else (a,'')
 if not M.connect_material_expressions(n,ch,b,p):raise RuntimeError('Cannot connect '+p)
def output(a,p):
 n,ch=a if isinstance(a,tuple) else (a,'')
 if not M.connect_material_property(n,ch,p):raise RuntimeError('Cannot connect material property')
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
textures={}
for kind in ['BaseColor','ORM']:
 src=O/'Textures'/('T_LMG201_S32_'+kind+'.png');task=u.AssetImportTask();task.filename=str(src);task.destination_path=P+'/Textures';task.destination_name=src.stem;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+src.stem)
 if not tex or not task.imported_object_paths:raise RuntimeError('Texture import failed '+kind)
 tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if kind=='BaseColor' else u.TextureCompressionSettings.TC_MASKS);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);save(tex);textures[kind]=tex
textures['Normal']=u.load_asset('/Game/Weapons/LMG201/Install30/Textures/T_201_R29_Surface_Normal')
materials={}
for kind in ['Surface','Steel','Interior']:
 name='M_LMG201_S32_'+kind;mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
 mat.set_editor_property('used_with_skeletal_mesh',True);mat.set_editor_property('two_sided',False);mat.set_editor_property('automatically_set_usage_in_editor',False)
 if kind=='Surface':
  samples={k:node(mat,u.MaterialExpressionTextureSample,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if k=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if k=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS) for k,t in textures.items()}
  base=(samples['BaseColor'],'RGB');rough=(samples['ORM'],'G');output((samples['ORM'],'B'),u.MaterialProperty.MP_METALLIC);output((samples['ORM'],'R'),u.MaterialProperty.MP_AMBIENT_OCCLUSION);output((samples['Normal'],'RGB'),u.MaterialProperty.MP_NORMAL)
 else:
  base=node(mat,u.MaterialExpressionVectorParameter,parameter_name='FinishColor',default_value=u.LinearColor(*((.014,.017,.021) if kind=='Interior' else (.022,.026,.031)),1))
  rough=scalar(mat,'DryRoughness',.76 if kind=='Interior' else .56);output(scalar(mat,'Metallic',.20 if kind=='Interior' else .65),u.MaterialProperty.MP_METALLIC)
 output(scalar(mat,'Specular',.28),u.MaterialProperty.MP_SPECULAR)
 wet=scalar(mat,'WeaponWetness',0);sat=node(mat,u.MaterialExpressionSaturate);wire(wet,sat,'')
 for original,mult,floor,prop in [(base,.87,None,u.MaterialProperty.MP_BASE_COLOR),(rough,.80,.58 if kind=='Interior' else .44,u.MaterialProperty.MP_ROUGHNESS)]:
  mul=node(mat,u.MaterialExpressionMultiply,const_b=mult);wire(original,mul,'A');wet_value=mul
  if floor is not None:
   bounded=node(mat,u.MaterialExpressionMax,const_b=floor);wire(mul,bounded,'A');wet_value=bounded
  blend=node(mat,u.MaterialExpressionLinearInterpolate);wire(original,blend,'A');wire(wet_value,blend,'B');wire(sat,blend,'Alpha');output(blend,prop)
 errors=M.recompile_material(mat)
 if errors:raise RuntimeError(str(errors))
 E.set_metadata_tag(mat,'201SurfaceRevision','Surface32 original mesh refinement; matte dark coating; UV0 structural normal preserved');save(mat);materials[kind]=mat.get_path_name()
(O/'materials.json').write_text(json.dumps({'status':'compiled_and_saved','materials':materials,'normal_reused':textures['Normal'].get_path_name()},indent=2));print('S32_MATERIALS_SAVED',materials,flush=True)
