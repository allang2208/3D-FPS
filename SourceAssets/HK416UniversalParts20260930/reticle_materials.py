"""EOTH optical materials, independent of gun-body and weather finishes."""
import unreal as u
from pathlib import Path
P=Path(__file__).parent;L=u.MaterialEditingLibrary
ROOT='/Game/Weapons/CommonHK41620260930/Optics20261001'
RETICLE=ROOT+'/M_EOTH_ClearReticle';GLASS=ROOT+'/M_EOTH_ClearGlass'
def node(m,cls,**values):
 n=L.create_material_expression(m,cls)
 for k,v in values.items():n.set_editor_property(k,v)
 return n
def wire(src,n,pin,channel=''):
 if not L.connect_material_expressions(src,channel,n,pin):raise RuntimeError('EOTH input '+pin)
def out(n,prop,channel=''):
 if not L.connect_material_property(n,channel,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('EOTH output '+prop)
def scalar(m,v):return node(m,u.MaterialExpressionConstant,r=v)
def color(m,rgb):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rgb,1))
def custom(m,code,inputs,size):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for name in inputs:
  pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n
def create(path):
 m=u.load_asset(path)
 if not m:m=u.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],ROOT,u.Material,u.MaterialFactoryNew())
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 m.set_editor_property('automatically_set_usage_in_editor',False)
 m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
 m.set_editor_property('two_sided',True);m.set_editor_property('disable_depth_test',False)
 m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_AFTER_DOF)
 return m
def build():
 reticle=create(RETICLE);reticle.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 reticle.set_editor_property('output_translucent_velocity',True)
 reticle.set_editor_property('is_translucency_velocity_from_depth',False)
 reticle.set_editor_property('opacity_mask_clip_value',.333)
 reticle.set_editor_property('enable_responsive_aa',False)
 shape=custom(reticle,(P/'EOTHReticle.hlsl').read_text(),{'UV':node(reticle,u.MaterialExpressionTextureCoordinate,coordinate_index=0)},3)
 outline=node(reticle,u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False);wire(shape,outline,'');out(outline,'OPACITY')
 emission=custom(reticle,'float ratio=saturate(Shape.r/max(Shape.g,.0001));return lerp(float3(.002,.001,.001),float3(1.4,.012,.004)*Shape.b,ratio);',{'Shape':shape},3)
 exposure=node(reticle,u.MaterialExpressionEyeAdaptationInverse)
 names=[str(x) for x in L.get_material_expression_input_names(exposure)]
 wire(emission,exposure,names[0]);wire(scalar(reticle,1.),exposure,names[1]);out(exposure,'EMISSIVE_COLOR')
 # Restrict history rejection to the glyph, leaving the window/background
 # alone. Its opaque coverage also supplies the actual rigid motion vector.
 response=node(reticle,u.MaterialExpressionTemporalResponsivenessOutput)
 amount=node(reticle,u.MaterialExpressionMultiply,const_b=.75);wire(outline,amount,'A');wire(amount,response,'')
 glass=create(GLASS);glass.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 glass.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
 out(color(glass,(.12,.17,.19)),'BASE_COLOR');out(scalar(glass,0.),'METALLIC')
 out(scalar(glass,.12),'ROUGHNESS');out(scalar(glass,.10),'SPECULAR');out(scalar(glass,1.),'REFRACTION')
 fresnel=node(glass,u.MaterialExpressionFresnel,exponent=5.,base_reflect_fraction=.01)
 opacity=custom(glass,'return .025+Fresnel*.065;',{'Fresnel':fresnel},1);out(opacity,'OPACITY')
 for m in (reticle,glass):
  errors=L.recompile_material(m)
  if errors:raise RuntimeError('EOTH shader compile '+m.get_name()+': '+str(errors))
  if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('EOTH material save '+m.get_name())
 return reticle,glass
