"""Install R29 baked PBR under a new namespace; old materials stay intact."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;SRC=O.parent/'Refine29/Textures';P='/Game/Weapons/LMG201/Install30'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; import deferred')
r={'status':'authoring','materials':{},'textures':{},'tested':False}
attributes=None
def record():(O/'materials.json').write_text(json.dumps(r,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
def node(mat,cls,**props):
 n=M.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin):
 n,p=a if isinstance(a,tuple) else (a,'')
 if not M.connect_material_expressions(n,p,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(a,prop):
 n,p=a if isinstance(a,tuple) else (a,'')
 if attributes is not None:
  pins={u.MaterialProperty.MP_BASE_COLOR:'BaseColor',u.MaterialProperty.MP_NORMAL:'Normal',u.MaterialProperty.MP_ROUGHNESS:'Roughness',
    u.MaterialProperty.MP_METALLIC:'Metallic',u.MaterialProperty.MP_SPECULAR:'Specular',u.MaterialProperty.MP_SUBSURFACE_COLOR:'SubsurfaceColor',
    u.MaterialProperty.MP_AMBIENT_OCCLUSION:'AmbientOcclusion','ClothFuzz':'ClearCoat'}
  if not M.connect_material_expressions(n,p,attributes,pins[prop]):raise RuntimeError('Cannot connect attribute '+str(prop))
 elif not M.connect_material_property(n,p,prop):raise RuntimeError('Cannot connect property '+str(prop))
def scalar(mat,name,v):return node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=v)
def color(mat,name,v):return node(mat,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*v,1))

textures={}
for group in ['Surface','AmmoBag']:
 textures[group]={}
 for kind in ['BaseColor','Normal','ORM']+(['Relief'] if group=='AmmoBag' else []):
  src=SRC/('T_201_R29_'+group+'_'+kind+'.png')
  task=u.AssetImportTask();task.filename=str(src);task.destination_path=P+'/Textures';task.destination_name=src.stem
  task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
  tex=u.load_asset(task.destination_path+'/'+task.destination_name)
  if not tex or not task.imported_object_paths:raise RuntimeError('Texture import failed '+str(src))
  tex.set_editor_property('srgb',kind=='BaseColor')
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if kind=='BaseColor' else u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS)
  tex.set_editor_property('flip_green_channel',kind=='Normal')
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
  save(tex);textures[group][kind]=tex;r['textures'][tex.get_path_name()]={'source':str(src),'green_flipped':kind=='Normal'};record()

for kind in ['Surface','Interior','Steel','Cloth']:
 attributes=None
 name='M_LMG201_R30_'+kind;mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);mat.set_editor_property('automatically_set_usage_in_editor',False)
 mat.set_editor_property('used_with_skeletal_mesh',kind!='Cloth');mat.set_editor_property('two_sided',False)
 if kind=='Cloth':
  mat.set_editor_property('use_material_attributes',True)
  attributes=node(mat,u.MaterialExpressionMakeMaterialAttributes)
  if not M.connect_material_property(attributes,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Cannot connect cloth attributes')
 if kind in ['Surface','Cloth']:
  group='AmmoBag' if kind=='Cloth' else 'Surface';samples={}
  for k,tex in textures[group].items():
   samples[k]=node(mat,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if k=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if k=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  base=(samples['BaseColor'],'RGB');rough=(samples['ORM'],'G')
  output((samples['ORM'],'R'),u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  output((samples['ORM'],'B'),u.MaterialProperty.MP_METALLIC)
  output((samples['Normal'],'RGB'),u.MaterialProperty.MP_NORMAL)
  if kind=='Cloth':
   mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)
   output(color(mat,'FabricFuzzTint',(.032,.038,.024)),u.MaterialProperty.MP_SUBSURFACE_COLOR)
   fuzz=node(mat,u.MaterialExpressionMultiply,const_b=.17);wire((samples['Relief'],'G'),fuzz,'A');output(fuzz,'ClothFuzz')
 else:
  base=color(mat,'FinishColor',(.017,.020,.023) if kind=='Interior' else (.022,.026,.031))
  rough=scalar(mat,'DryRoughness',.48 if kind=='Interior' else .37)
  output(scalar(mat,'Metallic',.65 if kind=='Interior' else .78),u.MaterialProperty.MP_METALLIC)
 output(scalar(mat,'Specular',.35 if kind=='Cloth' else .5),u.MaterialProperty.MP_SPECULAR)
 wet=scalar(mat,'WeaponWetness',0.);sat=node(mat,u.MaterialExpressionSaturate);wire(wet,sat,'')
 for original,amount,prop in [(base,.69 if kind=='Cloth' else .76,u.MaterialProperty.MP_BASE_COLOR),(rough,.70 if kind=='Cloth' else .48,u.MaterialProperty.MP_ROUGHNESS)]:
  mul=node(mat,u.MaterialExpressionMultiply,const_b=amount);wire(original,mul,'A')
  blend=node(mat,u.MaterialExpressionLinearInterpolate);wire(original,blend,'A');wire(mul,blend,'B');wire(sat,blend,'Alpha');output(blend,prop)
 errors=M.recompile_material(mat)
 if errors:raise RuntimeError('Material compile failed '+str(errors))
 E.set_metadata_tag(mat,'201SurfaceRevision','R29/Install30: faired Meshy source, retained coating, baked textile relief; no global material edits')
 save(mat);r['materials'][kind]=mat.get_path_name();record()
r['status']='compiled_and_saved';record();print('R30_PBR_SAVED',r['materials'],flush=True)
