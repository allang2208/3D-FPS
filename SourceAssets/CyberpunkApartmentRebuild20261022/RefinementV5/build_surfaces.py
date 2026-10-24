"""Apartment-only optical materials and normal completion; shared originals untouched."""
from pathlib import Path
import unreal as u,json,runpy
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT'];BASE=C['BASE']
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
NORMAL='/Game/SubstrateMaterials/Textures/01_Paints/T_Noise_N'
report=dict(stage='preparing',materials={},supplements={},preserved=[])
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing apartment optical dependency '+path)
 return a
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Optical material pin '+pin)
def scalar(m,v):return node(m,'Constant',r=v)
def rgb(m,v):return node(m,'Constant3Vector',constant=u.LinearColor(*v,1))
def custom(m,code,inputs):
 n=node(m,'Custom',code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
 pins=[]
 for k in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
 n.set_editor_property('inputs',pins)
 for k,v in inputs.items():wire(v,n,k)
 return n
def normal(m,strength=.01,period=1.8,path=NORMAL):
 uv=node(m,'TextureCoordinate',u_tiling=1.2/period,v_tiling=1.2/period)
 n=node(m,'TextureSample',texture=load(path),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv,n,'UVs')
 return custom(m,'return normalize(float3(N.xy*S,1));',{'N':n,'S':scalar(m,strength)})
def save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 if not E.save_loaded_asset(m,False):raise RuntimeError('Save optical material '+m.get_name())
def create(name):
 path=BASE+'/Materials/'+name
 m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 return m
def surface(key,color,rough,metal=0.,strength=.20,normal_path=NORMAL,thin=False):
 m=create('M_AP5_'+key);m.set_editor_property('used_with_nanite',not thin)
 m.set_editor_property('two_sided',thin)
 m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT if thin else u.MaterialShadingModel.MSM_DEFAULT_LIT)
 if thin:
  m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
  m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
  m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
  m.set_editor_property('allow_front_layer_translucency',True)
  m.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
  m.set_editor_property('disable_depth_test',False)
 slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_THIN_TRANSLUCENT if thin else u.MaterialShadingModel.MSM_DEFAULT_LIT)
 n=normal(m,strength,1.8 if thin else .50,normal_path)
 for source,pin,prop in [(rgb(m,(0,0,0) if thin else color),'BaseColor','BASE_COLOR'),(n,'Normal','NORMAL'),
    (scalar(m,rough),'Roughness','ROUGHNESS'),(scalar(m,metal),'Metallic','METALLIC'),(scalar(m,.5),'Specular','SPECULAR')]:
  wire(source,slab,pin);L.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+prop))
 if thin:
  trans=rgb(m,color);coverage=scalar(m,1)
  wire(trans,slab,'Thin Translucent Transmittance Color');wire(coverage,slab,'Thin Translucent Surface Coverage')
  # UE 5.8 converts Thin Translucent Opacity into an opaque coating:
  # TransColor = lerp(TransmittanceColor, 0, Opacity). Surface coverage is separate.
  # Clear windows retain full reflective coverage, with no opaque coating.
  opacity=scalar(m,0. if key=='WindowGlass' else 1.)
  wire(opacity,slab,'Opacity');L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
  output=node(m,'ThinTranslucentMaterialOutput');pins=L.get_material_expression_input_names(output)
  wire(trans,output,str(pins[0]));wire(coverage,output,str(pins[1]))
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);save(m)
 report['materials'][key]=dict(path=m.get_path_name(),normal=normal_path,normal_strength=strength,roughness=rough,thin_transmission=thin)
 return m
def build():
 surface('WindowGlass',(.985,.992,.998),.028,strength=.008,thin=True)
 surface('ShowerGlass',(.94,.975,.985),.085,strength=.018,thin=True)
 surface('Mirror',(.91,.92,.94),.016,1.,.0015)
 ceramic='/Game/Dungeons/FacilityTransit20261007/RefineV2/Textures/T_FT2_Ceramic_NormalDX'
 surface('BathTile',(.16,.185,.205),.48,strength=.32,normal_path=ceramic)
 surface('BathWall',(.32,.35,.38),.24,strength=.18,normal_path=ceramic)
 inventory=json.loads((ROOT/'component-audit-before.json').read_text('utf8'))
 used={s.get('material') for c in inventory['components'] if c['actor'].startswith(('AP_','Door_')) and c['visible'] and not c['hidden_in_game'] for s in c['slots']}
 for path,data in inventory['materials'].items():
  if path not in used or data['normal_textures']:continue
  src=load(path);base=src
  while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
  if not isinstance(base,u.Material):continue
  if 'Coffee_' in base.get_name() or 'Crema_' in base.get_name():
   report['preserved'].append(dict(path=path,reason='smooth liquid surface; no manufactured micro-relief'));continue
  front=L.get_material_property_input_node(base,u.MaterialProperty.MP_FRONT_MATERIAL)
  if isinstance(front,u.MaterialExpressionSubstrateUnlitBSDF) or base.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_UNLIT:
   report['preserved'].append(dict(path=path,reason='pure unlit emission; normal has no shading effect'));continue
  name='M_AP5_Surface_'+base.get_name();dest=BASE+'/Materials/'+name
  m=load(dest) if E.does_asset_exist(dest) else A.duplicate_asset(name,BASE+'/Materials',base)
  # Re-runs reuse the last saved supplement, avoiding duplicate graph branches.
  if not E.get_metadata_tag(m,'ApartmentV5.Normal'):
   n=normal(m,.010 if any(t in name for t in ('UI','Glass','Screen')) else .025,.70)
   front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
   if front:
    if 'Normal' not in [str(s) for s in L.get_material_expression_input_names(front)]:
     report['preserved'].append(dict(path=path,reason='specialty front surface with no normal input'));continue
    wire(n,front,'Normal')
   L.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
   E.set_metadata_tag(m,'ApartmentV5.Normal',NORMAL);save(m)
  report['supplements'][path]=dict(path=m.get_path_name(),normal=NORMAL)
 report['stage']='surfaces_saved';(ROOT/'surfaces_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print('APARTMENT_V5_SURFACES_SAVED',len(report['materials']),len(report['supplements']))
if __name__=='__main__':build()
