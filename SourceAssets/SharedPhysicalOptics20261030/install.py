"""Save shared lens/reticle materials. Original model assets are untouched."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent
D='/Game/Weapons/SharedPhysicalOptics20261030'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
report={'complete':False,'saved':[],'runtime_tested':False}
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 report['saved'].append(asset.get_path_name())
 (O/'install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
dirty={str(p.get_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('Unsaved shared optics edits retained')
t=u.AssetImportTask();t.filename=str(O/'T_OpticNumerals.png');t.destination_path=D;t.destination_name='T_OpticNumerals'
t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
glyphs=u.load_asset(D+'/T_OpticNumerals');glyphs.srgb=False
glyphs.compression_settings=u.TextureCompressionSettings.TC_MASKS
glyphs.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
glyphs.address_x=glyphs.address_y=u.TextureAddress.TA_CLAMP
save(glyphs)
def material(name):
 m=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(m);return m
m=material('M_PhysicalScopeLens')
def node(cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,output,b,pin):
 if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material pin '+pin)
def custom(code,inputs,result=u.CustomMaterialOutputType.CMOT_FLOAT1):
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n=node(u.MaterialExpressionCustom,code=code,output_type=result,inputs=pins)
 for name,(src,out) in inputs.items():wire(src,out,n,name)
 return n
def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def vector(name,value):return node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value))
def prop(n,name):
 if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError(name)
screen=node(u.MaterialExpressionScreenPosition)
scale=vector('ScreenToLens',(4,2.25,0,0));fov=scalar('CaptureTanHalfFOV',.025);style=scalar('ReticleStyle',0)
blend=scalar('LensBlend',0)
scene=node(u.MaterialExpressionTextureObjectParameter,parameter_name='ScopeScene',texture=u.load_asset('/Engine/EngineResources/Black'))
glyph=node(u.MaterialExpressionTextureObjectParameter,parameter_name='Glyphs',texture=glyphs)
picture=custom((O/'lens.hlsl').read_text(),{'ScreenUV':(screen,'ViewportUV'),'ScreenToLens':(scale,'RGB'),
 'CaptureTanHalfFOV':(fov,''),'ReticleStyle':(style,''),'Scene':(scene,''),'Glyphs':(glyph,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
position=node(u.MaterialExpressionWorldPosition)
center=vector('LensCenter',(0,0,0,0));forward=vector('LensForward',(1,0,0,0));depth=scalar('RearDepth',1)
alpha=custom('return saturate(Blend)*step(dot(Position-Center,Forward),Depth);',
 {'Blend':(blend,''),'Position':(position,''),'Center':(center,'RGB'),'Forward':(forward,'RGB'),'Depth':(depth,'')})
fresnel=node(u.MaterialExpressionFresnel,exponent=4.0,base_reflect_fraction=0.0)
opacity=custom('return lerp(lerp(.018,.16,Fresnel),1,Alpha);',{'Fresnel':(fresnel,''),'Alpha':(alpha,'')})
emissive=custom('return Picture*Alpha/max(Opacity,.001);',{'Picture':(picture,''),'Alpha':(alpha,''),'Opacity':(opacity,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
base=custom('return float3(.07,.13,.15)*(1-Alpha);',{'Alpha':(alpha,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
spec=custom('return .35*(1-Alpha);',{'Alpha':(alpha,'')})
for n,name in [(emissive,'EMISSIVE_COLOR'),(base,'BASE_COLOR'),(opacity,'OPACITY'),(spec,'SPECULAR'),
 (node(u.MaterialExpressionConstant,r=.045),'ROUGHNESS'),(node(u.MaterialExpressionConstant,r=0),'METALLIC')]:prop(n,name)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('two_sided',True)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
m.set_editor_property('automatically_set_usage_in_editor',False)
L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_MORPH_TARGETS,True)
errors=L.recompile_material(m)
if errors:raise RuntimeError(str(errors))
save(m)
m_path=D+'/M_PhysicalThermalScene'
thermal=u.load_asset(m_path) if E.does_asset_exist(m_path) else E.duplicate_asset('/Game/Weapons/ThermalScope20261006/Runtime/M_ThermalScene',m_path)
if not thermal:raise RuntimeError('Cannot create lens thermal material')
effect=L.get_material_property_input_node(thermal,u.MaterialProperty.MP_EMISSIVE_COLOR)
if not isinstance(effect,u.MaterialExpressionCustom):raise RuntimeError('Unexpected source thermal graph')
effect.set_editor_property('code',(O/'thermal_scene.hlsl').read_text(encoding='utf-8'))
effect.set_editor_property('desc','Lens-only thermal with lifted cold-scene detail; original heat/depth occlusion preserved')
L.recompile_material(thermal);save(thermal)
m=material('M_PhysicalScopeHideReticle')
m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
prop(node(u.MaterialExpressionConstant,r=0),'OPACITY_MASK')
L.recompile_material(m);save(m)
report['complete']=True
(O/'install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SHARED_PHYSICAL_OPTICS_SAVED',json.dumps(report),flush=True)
