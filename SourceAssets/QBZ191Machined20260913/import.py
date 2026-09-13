"""Install the authored mesh/material revision on the existing QBZ skeleton."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/QBZ191';D=P+'/Machined20260913';A=u.AssetToolsHelpers.get_asset_tools();lib=u.MaterialEditingLibrary
mesh=u.load_asset(P+'/Calibrated/SK_QBZ191_Manny');skeleton=mesh.skeleton
bindings={str(x.material_slot_name):x.material_interface for x in mesh.materials}
materials={}
def create(name):
 path=D+'/Materials/'+name
 m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 lib.delete_all_material_expressions(m);lib.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);return m
for part in ['Body','Magazine','Polymer','Steel','Irons_Machined','Irons_Inner']:
 name='M_QBZ191_'+part;m=create(name)
 def node(cls):return lib.create_material_expression(m,cls)
 def c(v):n=node(u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
 def color(v):n=node(u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
 def wire(a,out,b,pin):
  if not lib.connect_material_expressions(a,out,b,pin):raise RuntimeError('Failed material connection: '+part+' '+pin)
 def output(n,p,out=''):
  if not lib.connect_material_property(n,out,p):raise RuntimeError('Failed material property: '+part)
 def mul(a,b,channel='R'):
  n=node(u.MaterialExpressionMultiply);wire(a,channel,n,'A');wire(b,'',n,'B');return n
 if part.startswith('Irons_'):
  inner=part=='Irons_Inner'
  output(color((.008,.010,.012) if inner else (.028,.032,.036)),u.MaterialProperty.MP_BASE_COLOR)
  output(c(.15 if inner else .78),u.MaterialProperty.MP_METALLIC)
  output(c(.84 if inner else .58),u.MaterialProperty.MP_ROUGHNESS)
 else:
  poly=part=='Polymer';steel=part=='Steel';mag=part=='Magazine';tp='Magazine' if mag else 'Body';textures={}
  for kind in ['BaseColor','Metallic','Roughness','Normal']:
   n=node(u.MaterialExpressionTextureSample);n.set_editor_property('texture',u.load_asset(P+'/Textures/T_QBZ191_'+tp+'_'+kind))
   n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE);textures[kind]=n
  output(textures['BaseColor'],u.MaterialProperty.MP_BASE_COLOR,'RGB')
  output(c(.02) if poly else mul(textures['Metallic'],c(1. if steel else .85)),u.MaterialProperty.MP_METALLIC)
  rough=mul(textures['Roughness'],c(.45 if poly else .55));add=node(u.MaterialExpressionAdd);wire(rough,'',add,'A');wire(c(.42 if poly else .25),'',add,'B')
  clamp=node(u.MaterialExpressionClamp);wire(add,'',clamp,'');clamp.set_editor_property('min_default',.58 if poly else .44 if steel else .47);clamp.set_editor_property('max_default',1.);output(clamp,u.MaterialProperty.MP_ROUGHNESS)
  normal=node(u.MaterialExpressionLinearInterpolate);wire(color((0,0,1)),'',normal,'A');wire(textures['Normal'],'RGB',normal,'B');wire(c(.24 if poly else .35 if mag else .28),'',normal,'Alpha');output(normal,u.MaterialProperty.MP_NORMAL)
 lib.recompile_material(m)
 if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Material save failed: '+part)
 materials[name]=m
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
opt.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
opt.skeletal_mesh_import_data.set_editor_property('normal_generation_method',u.FBXNormalGenerationMethod.MIKK_T_SPACE)
task=u.AssetImportTask();task.filename=str(O/'SK_QBZ191_Manny.fbx');task.destination_path=P+'/Calibrated';task.destination_name='SK_QBZ191_Manny';task.options=opt;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
mesh=u.load_asset(P+'/Calibrated/SK_QBZ191_Manny');slots=mesh.materials
for i,slot in enumerate(slots):
 name=str(slot.material_slot_name)
 if name in materials:slot.material_interface=materials[name]
 elif name in bindings:slot.material_interface=bindings[name]
 else:raise RuntimeError('No authoring material for slot: '+name)
 slots[i]=slot
mesh.set_editor_property('materials',slots)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),'materials':{str(x.material_slot_name):x.material_interface.get_path_name() for x in slots},'source_fbx':task.filename,'status':'imported; no gameplay or rendered acceptance'},indent=2))
u.log('QBZ_MACHINED_IMPORT_COMPLETE')
