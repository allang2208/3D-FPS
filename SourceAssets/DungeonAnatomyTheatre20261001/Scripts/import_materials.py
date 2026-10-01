"""Own materials and procedural wood maps; shared hospital materials stay intact."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];CFG=json.loads((ROOT/'Config/room.json').read_text('utf-8'))
BASE=CFG['ue_base'];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
saved=[]
def save(o):
 if not E.save_loaded_asset(o,False):raise RuntimeError('Material save failed '+o.get_path_name())
 saved.append(o.get_path_name())
textures={}
for suffix in ('BaseColor','NormalDX','ORM'):
 name='T_TheatreWood_'+suffix;path=BASE+'/Textures/'+name
 t=u.load_asset(path) if E.does_asset_exist(path) else None
 if not t:
  task=u.AssetImportTask();task.filename=str(ROOT/'Authored/Textures'/(name+'.png'));task.destination_path=BASE+'/Textures';task.destination_name=name
  task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(path)
  if not t:raise RuntimeError('Missing texture '+path)
  t.set_editor_property('srgb',suffix=='BaseColor');t.set_editor_property('never_stream',False)
  t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if suffix=='BaseColor' else u.TextureCompressionSettings.TC_NORMALMAP if suffix=='NormalDX' else u.TextureCompressionSettings.TC_MASKS)
  if suffix=='NormalDX':t.set_editor_property('flip_green_channel',False)
  save(t)
 textures[suffix]=t
for key,tint,rough,metal in [('Wood',(.14,.064,.025),.68,0),('Ceramic',(.18,.215,.195),.7,0),('Chalkboard',(.012,.022,.018),.91,0),('LampGlass',(.34,.42,.40),.28,0)]:
 name='M_Theatre_'+key;path=BASE+'/Materials/'+name
 if E.does_asset_exist(path):continue
 m=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
 slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 if key=='Wood':
  for suffix in textures:
   node=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D);node.set_editor_property('parameter_name',suffix);node.set_editor_property('texture',textures[suffix])
   node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='NormalDX' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
   channels=[('RGB','BASE_COLOR','BaseColor')] if suffix=='BaseColor' else [('RGB','NORMAL','Normal')] if suffix=='NormalDX' else [('R','AMBIENT_OCCLUSION',None),('G','ROUGHNESS','Roughness'),('B','METALLIC','Metallic')]
   for output,prop,pin in channels:
    L.connect_material_property(node,output,getattr(u.MaterialProperty,'MP_'+prop))
    if pin:L.connect_material_expressions(node,output,slab,pin)
 else:
  for prop,pin,value in [('BASE_COLOR','BaseColor',tint),('ROUGHNESS','Roughness',rough),('METALLIC','Metallic',metal)]:
   cls=u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant
   node=L.create_material_expression(m,cls)
   node.set_editor_property('constant',u.LinearColor(*value,1)) if isinstance(value,tuple) else node.set_editor_property('r',value)
   L.connect_material_property(node,'',getattr(u.MaterialProperty,'MP_'+prop));L.connect_material_expressions(node,'',slab,pin)
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compilation failed '+str(errors))
 L.layout_material_expressions(m);save(m)
(ROOT/'Receipts/materials.json').write_text(json.dumps(dict(saved_assets=saved,stage='materials_saved',tests_run=False),indent=2),encoding='utf-8')
print('ANATOMY_THEATRE_MATERIALS_SAVED')
