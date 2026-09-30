"""Build and save local receiver/precision finishes with the existing wetness input."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/Detail35';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; material save deferred')
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
 if not M.connect_material_property(n,ch,p):raise RuntimeError('Cannot connect output')
def scalar(m,n,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=n,default_value=v)
textures={}
for kind in ['BaseColor','ORM','Normal']:
 src=O/'Textures'/('T_LMG201_D35_Receiver_'+kind+'.png');t=u.AssetImportTask();t.filename=str(src);t.destination_path=P+'/Textures';t.destination_name=src.stem;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
 if not tex or not t.imported_object_paths:raise RuntimeError('Cannot import '+kind)
 tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('compression_settings',{'BaseColor':u.TextureCompressionSettings.TC_BC7,'ORM':u.TextureCompressionSettings.TC_MASKS,'Normal':u.TextureCompressionSettings.TC_NORMALMAP}[kind]);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
 if kind=='Normal':tex.set_editor_property('flip_green_channel',False)
 save(tex);textures[kind]=tex
recipes={'Coat':((.021,.026,.031),.35,.58),'Interior':((.015,.019,.023),.42,.64),'Satin':((.040,.046,.052),.78,.42),'Sight':((.014,.017,.020),.2,.68)}
materials={}
for kind in ['Receiver',*recipes]:
 name='M_LMG201_D35_'+kind;mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat);mat.set_editor_property('used_with_skeletal_mesh',True);mat.set_editor_property('two_sided',False);mat.set_editor_property('automatically_set_usage_in_editor',False)
 if kind=='Receiver':
  samples={k:node(mat,u.MaterialExpressionTextureSample,texture=v,sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[k]) for k,v in textures.items()}
  base=(samples['BaseColor'],'RGB');rough=(samples['ORM'],'G');output((samples['ORM'],'B'),u.MaterialProperty.MP_METALLIC);output((samples['ORM'],'R'),u.MaterialProperty.MP_AMBIENT_OCCLUSION);output((samples['Normal'],'RGB'),u.MaterialProperty.MP_NORMAL)
 else:
  color,metal,r=recipes[kind];base=node(mat,u.MaterialExpressionVectorParameter,parameter_name='FinishColor',default_value=u.LinearColor(*color,1));rough=scalar(mat,'DryRoughness',r);output(scalar(mat,'Metallic',metal),u.MaterialProperty.MP_METALLIC)
 output(scalar(mat,'Specular',.28),u.MaterialProperty.MP_SPECULAR);wet=scalar(mat,'WeaponWetness',0);sat=node(mat,u.MaterialExpressionSaturate);wire(wet,sat,'')
 for original,mult,floor,prop in [(base,.90,None,u.MaterialProperty.MP_BASE_COLOR),(rough,.85,.38 if kind=='Satin' else .52 if kind in ['Interior','Sight'] else .48,u.MaterialProperty.MP_ROUGHNESS)]:
  mul=node(mat,u.MaterialExpressionMultiply,const_b=mult);wire(original,mul,'A');wet_value=mul
  if floor is not None:
   bounded=node(mat,u.MaterialExpressionMax,const_b=floor);wire(mul,bounded,'A');wet_value=bounded
  blend=node(mat,u.MaterialExpressionLinearInterpolate);wire(original,blend,'A');wire(wet_value,blend,'B');wire(sat,blend,'Alpha');output(blend,prop)
 errors=M.recompile_material(mat)
 if errors:raise RuntimeError(str(errors))
 E.set_metadata_tag(mat,'201SurfaceRevision','Detail35: local panel cleanup; precision parts use dedicated coating rather than generated atlas noise');save(mat);materials[kind]=mat.get_path_name()
model=json.loads((O/'model.json').read_text());bindings={k:materials[v] for k,v in model['material_roles'].items()}
bindings.update(M_LMG201_D35_ControlSatin=materials['Satin'],M_LMG201_D35_ControlCoat=materials['Coat'])
original=json.loads((O/'inputs.json').read_text())['assets']['Body']['materials']
for s in original:
 if '_R30_' in s['slot']:bindings[s['slot']]=s['asset']
(O/'materials.json').write_text(json.dumps({'status':'compiled_and_saved','materials':materials,'slot_bindings':bindings,'textures':{k:v.get_path_name() for k,v in textures.items()}},indent=2));print('DETAIL35_MATERIALS_SAVED',materials,flush=True)
