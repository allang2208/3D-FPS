import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/BeltRebuild52'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def node(m,c,**props):
 a=L.create_material_expression(m,c)
 for k,v in props.items():a.set_editor_property(k,v)
 return a
def wire(a,output,b,pin):
 if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material pin '+pin)
def out(a,p):
 if not L.connect_material_property(a,'',p):raise RuntimeError('Material output')
textures={}
for name,normal in [('T_B52_MetalFinish',False),('T_B52_MicroNormal',True)]:
 path=P+'/Textures/'+name;t=u.load_asset(path)
 if not t:
  task=u.AssetImportTask();task.filename=str(O/'Textures'/(name+'.png'));task.destination_path=P+'/Textures';task.destination_name=name;task.automated=True;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(path)
 if not t:raise RuntimeError('Texture import failed '+name)
 t.set_editor_property('srgb',False)
 t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS)
 save(t);textures[name]=t
path=P+'/Materials/M_B52_Metal';m=u.load_asset(path)
if not m:
 m=A.create_asset('M_B52_Metal',P+'/Materials',u.Material,u.MaterialFactoryNew())
 L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 color=node(m,u.MaterialExpressionVectorParameter,parameter_name='MetalColor',default_value=u.LinearColor(.48,.315,.105,1))
 vc=node(m,u.MaterialExpressionVertexColor);mul=node(m,u.MaterialExpressionMultiply);wire(color,'RGB',mul,'A');wire(vc,'',mul,'B');out(mul,u.MaterialProperty.MP_BASE_COLOR)
 metal=node(m,u.MaterialExpressionScalarParameter,parameter_name='Metallic',default_value=.95);out(metal,u.MaterialProperty.MP_METALLIC)
 rough=node(m,u.MaterialExpressionScalarParameter,parameter_name='Roughness',default_value=.31)
 tex=node(m,u.MaterialExpressionTextureSample,texture=textures['T_B52_MetalFinish'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 bias=node(m,u.MaterialExpressionSubtract,const_b=.5);wire(tex,'R',bias,'A')
 fine=node(m,u.MaterialExpressionMultiply,const_b=.05);wire(bias,'',fine,'A')
 add=node(m,u.MaterialExpressionAdd);wire(rough,'',add,'A');wire(fine,'',add,'B')
 wet=node(m,u.MaterialExpressionScalarParameter,parameter_name='Wetness',default_value=0.)
 wetmul=node(m,u.MaterialExpressionMultiply,const_b=.15);wire(wet,'',wetmul,'A')
 wetfactor=node(m,u.MaterialExpressionOneMinus);wire(wetmul,'',wetfactor,'')
 finalrough=node(m,u.MaterialExpressionMultiply);wire(add,'',finalrough,'A');wire(wetfactor,'',finalrough,'B');out(finalrough,u.MaterialProperty.MP_ROUGHNESS)
 normal=node(m,u.MaterialExpressionTextureSample,texture=textures['T_B52_MicroNormal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 out(normal,u.MaterialProperty.MP_NORMAL)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Metal material compile '+str(errors))
 save(m)
materials={}
for role,spec in json.loads((O/'layout.json').read_text())['materials'].items():
 path=P+'/Materials/MI_B52_'+role;mi=u.load_asset(path)
 if not mi:mi=A.create_asset('MI_B52_'+role,P+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 L.set_material_instance_parent(mi,m)
 L.set_material_instance_vector_parameter_value(mi,'MetalColor',u.LinearColor(*spec['color'],1))
 L.set_material_instance_scalar_parameter_value(mi,'Roughness',spec['roughness'])
 L.set_material_instance_scalar_parameter_value(mi,'Metallic',.93 if role=='Link' else .98)
 L.update_material_instance(mi);save(mi);materials[role]=path
(O/'materials.json').write_text(json.dumps(materials,indent=2))
print('BELT52_MATERIALS_SAVED',materials,flush=True)
