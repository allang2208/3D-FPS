from pathlib import Path
import json,sys
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_specs import *
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def load(path):
 o=u.load_asset(path)
 if not o:raise RuntimeError('Missing PBR source '+path)
 return o
def save(o):
 if not E.save_loaded_asset(o,False):raise RuntimeError('PBR save failed '+o.get_path_name())
def node(m,kind,**props):
 o=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():o.set_editor_property(k,v)
 return o
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('PBR pin '+pin)
def scalar(m,value):return node(m,'Constant',r=value)
def rgb(m,value):return node(m,'Constant3Vector',constant=u.LinearColor(*value,1))
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,v in inputs.items():wire(v,n,name)
 return n
def tex_sample(m,path,uv,normal=False):
 t=load(path);comp=str(t.get_editor_property('compression_settings'))
 st=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if t.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'MASKS' in comp else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
 n=node(m,'TextureSample',texture=t,sampler_type=st);wire(uv,n,'UVs');return n
def build():
 report={'stage':'preparing','materials':{},'reused_textures':[],'normal_contract':'existing library conventions retained; new etch DirectX no flip'}
 for suffix in ('N','ORM'):
  t=u.AssetImportTask();t.filename=str(ROOT/'Textures'/('T_AP4_Etch_'+suffix+'.png'));t.destination_path=BASE+'/Textures';t.destination_name='T_AP4_Etch_'+suffix
  t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=load(BASE+'/Textures/T_AP4_Etch_'+suffix)
  tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='N' else u.TextureCompressionSettings.TC_MASKS)
  tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE);tex.set_editor_property('never_stream',False)
  if suffix=='N':tex.set_editor_property('flip_green_channel',False)
  save(tex)
 for role,spec in SPECS.items():
  name='M_AP4_'+role;path=BASE+'/Materials/'+name
  m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
  for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
  m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
  slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
  coord=node(m,'TextureCoordinate');uvscale=node(m,'ScalarParameter',parameter_name='UVScale',default_value=spec['uv_m']/spec['period_m'])
  uv=node(m,'Multiply');wire(coord,uv,'A');wire(uvscale,uv,'B')
  color=rgb(m,spec['color'])
  if spec['base']:
   source=tex_sample(m,spec['base'],uv)
   color=custom(m,'float l=dot(C.rgb,float3(.2126,.7152,.0722)); return Tint*lerp(.65,1.25,saturate(l*2.2));',{'C':source,'Tint':color})
  normal=tex_sample(m,spec['normal'],uv,True)
  strength=node(m,'ScalarParameter',parameter_name='NormalStrength',default_value=spec['strength'])
  normal=custom(m,'return normalize(float3(N.xy*S,lerp(1.0,N.z,saturate(S))));',{'N':normal,'S':strength})
  if spec['rough']:
   r=tex_sample(m,spec['rough'],uv)
   rough=custom(m,'return lerp(Low,High,saturate(R.r));',{'R':r,'Low':scalar(m,spec['rough_range'][0]),'High':scalar(m,spec['rough_range'][1])},1)
  else:rough=scalar(m,sum(spec['rough_range'])/2)
  ao=scalar(m,1.)
  if role=='Armor':
   detail=tex_sample(m,BASE+'/Textures/T_AP4_Etch_N',uv,True)
   normal=custom(m,'float3 t=B+float3(0,0,1); float3 u=D*float3(-1,-1,1); return normalize(t*dot(t,u)/max(t.z,.001)-u);',{'B':normal,'D':detail})
   packed=tex_sample(m,BASE+'/Textures/T_AP4_Etch_ORM',uv)
   rough=custom(m,'return clamp(R*.70+Packed.g*.30,.20,.65);',{'R':rough,'Packed':packed},1)
   ao=custom(m,'return Packed.r;',{'Packed':packed},1)
  for source,pin,prop in [(color,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),
   (scalar(m,spec['metal']),'Metallic','METALLIC'),(scalar(m,.35),'Specular','SPECULAR')]:
   wire(source,slab,pin);L.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+prop))
  L.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
  errors=L.recompile_material(m)
  if errors:raise RuntimeError(str(errors))
  save(m)
  mi_name='MI_AP4_'+role;mi_path=BASE+'/Materials/'+mi_name
  mi=load(mi_path) if E.does_asset_exist(mi_path) else A.create_asset(mi_name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.set_material_instance_parent(mi,m);L.update_material_instance(mi);save(mi)
  report['materials'][role]=dict(path=mi_path,normal=spec['normal'],period_m=spec['period_m'],normal_input_connected=True,rough_range=spec['rough_range'])
  report['reused_textures'].extend(p for p in (spec['normal'],spec['rough'],spec['base']) if p)
  (ROOT/'surfaces_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 report['reused_textures']=sorted(set(report['reused_textures']));report['stage']='surfaces_saved'
 (ROOT/'surfaces_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print('APARTMENT_PBR_SURFACES_SAVED',len(report['materials']))
 return report
if __name__=='__main__':build()
