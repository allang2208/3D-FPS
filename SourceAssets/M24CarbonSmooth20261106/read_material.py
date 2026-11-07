from pathlib import Path
import unreal as u,json
O=Path(__file__).resolve().parent
mat=u.load_asset('/Game/Weapons/M24/CarbonSpine20261104/Meshy1105135808/M_M24_Meshy1105135808')
r={'material':mat.get_path_name(),'properties':{},'meshes':{}}
for name in ('BASE_COLOR','ROUGHNESS','METALLIC','NORMAL'):
    node=u.MaterialEditingLibrary.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+name))
    texture=node.get_editor_property('texture') if node else None
    r['properties'][name]={'node':node.get_class().get_name() if node else None,
        'texture':texture.get_path_name() if texture else None,'uv':node.get_editor_property('const_coordinate') if node else None}
for kind in ('Native','Advanced'):
    obj=u.load_asset('/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_'+kind)
    r['meshes'][kind]={'source':list(obj.get_editor_property('asset_import_data').extract_filenames()),
        'uv_channels':u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_num_uv_channels(obj,0)}
(O/'material_read.json').write_text(json.dumps(r,indent=2))
print('M24_MATERIAL_SOURCE',r)
