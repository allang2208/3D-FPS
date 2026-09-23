import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922/Bipod07'
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'bindings':{},'sources':{},'saved':[]}
manifest=json.loads((O/'surface_manifest.json').read_text())
live=json.loads((O/'qbz_live_materials.json').read_text())
def save(asset):
 if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 report['saved'].append(asset.get_path_name())
for group,info in manifest['groups'].items():
 original=next(s['material'] for s in live['slots'] if s['slot']=='M_QBZ191_Wear_'+group)
 name='M_PKM_QBZ_'+group;path=P+'/Materials/'+name
 mat=u.load_asset(path) if L.does_asset_exist(path) else L.duplicate_asset(original,path)
 textures={}
 for channel,file in info['textures'].items():
  task=u.AssetImportTask();task.filename=file;task.destination_path=P+'/Textures';task.destination_name='T_PKM_QBZ_'+group+'_'+channel;task.automated=True;task.replace_existing=True;task.save=False
  A.import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+task.destination_name)
  if not tex:raise RuntimeError('Texture import failed '+file)
  tex.set_editor_property('srgb',channel=='BaseColor')
  if channel=='Normal':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
  elif channel=='ORM':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
  save(tex);textures[channel]=tex
 visited=set()
 def replace(node):
  if not node or node.get_path_name() in visited:return
  visited.add(node.get_path_name())
  if isinstance(node,u.MaterialExpressionTextureSample):
   current=node.get_editor_property('texture')
   if current:
    channel=next((c for c in textures if current.get_name().endswith('_'+c)),None)
    if channel:node.set_editor_property('texture',textures[channel])
  for child in M.get_inputs_for_material_expression(mat,node):replace(child)
 for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_AMBIENT_OCCLUSION]:
  replace(M.get_material_property_input_node(mat,prop))
 M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);M.recompile_material(mat)
 L.set_metadata_tag(mat,'PKM_QBZ_Source',original);save(mat)
 report['bindings'][info['material']]=mat.get_path_name();report['sources'][info['material']]=original
for name in ['PKM_LaminatedWood','PKM_WoodGripPanel']:
 report['bindings'][name]='/Game/Weapons/PKMLowpoly20260922/Refinement06/Materials/M_'+name+'_06'
(O/'surface_import.json').write_text(json.dumps(report,indent=2));print('PKM07: QBZ material graph copies and private PKM PBR atlases saved.')
