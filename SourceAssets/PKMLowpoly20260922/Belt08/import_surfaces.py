import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
manifest=json.loads((O/'surface_manifest.json').read_text())
source=P+'/Bipod07/Materials/M_PKM_QBZ_Body';path=P+'/Belt08/Materials/M_PKM_BeltLinkSteel'
mat=u.load_asset(path) if L.does_asset_exist(path) else L.duplicate_asset(source,path)
textures={}
for channel,file in manifest['textures'].items():
 task=u.AssetImportTask();task.filename=file;task.destination_path=P+'/Belt08/Textures';task.destination_name='T_PKM_Belt08_'+channel;task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+task.destination_name)
 if not tex:raise RuntimeError('PKM08 texture import failed '+file)
 tex.set_editor_property('srgb',channel=='BaseColor')
 if channel=='Normal':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
 elif channel=='ORM':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
 if not L.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed')
 textures[channel]=tex
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
for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_AMBIENT_OCCLUSION]:replace(M.get_material_property_input_node(mat,prop))
M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);M.recompile_material(mat)
L.set_metadata_tag(mat,'PKM_QBZ_Source',source)
if not L.save_loaded_asset(mat,False):raise RuntimeError('Material save failed')
report={'bindings':json.loads((O.parent/'Bipod07/surface_import.json').read_text())['bindings'],
        'sources':{'PKM_BeltLinkSteel':source},'saved':[t.get_path_name() for t in textures.values()]+[mat.get_path_name()]}
report['bindings']['PKM_BeltLinkSteel']=mat.get_path_name()
(O/'surface_import.json').write_text(json.dumps(report,indent=2));print('PKM08 link coating and maps saved.')
