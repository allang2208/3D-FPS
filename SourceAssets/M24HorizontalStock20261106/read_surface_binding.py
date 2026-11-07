from pathlib import Path
import unreal as u,json
O=Path(__file__).resolve().parent
p='/Game/Weapons/M24/CarbonSpine20261104/Meshy1105135808/M_M24_Meshy1105135808'
m=u.load_asset(p);L=u.MaterialEditingLibrary
r={'material':m.get_path_name(),'asset_writes':False,'outputs':{}}
for label,prop in [('base_color',u.MaterialProperty.MP_BASE_COLOR),('normal',u.MaterialProperty.MP_NORMAL)]:
    node=L.get_material_property_input_node(m,prop)
    tex=node.get_editor_property('texture') if node else None
    r['outputs'][label]={'connected':bool(node),'texture':tex.get_path_name() if tex else None,
        'sampler':str(node.get_editor_property('sampler_type')) if node else None,
        'compression':str(tex.get_editor_property('compression_settings')) if tex else None,
        'srgb':tex.get_editor_property('srgb') if tex else None}
(O/'VisualReview/surface_binding.json').write_text(json.dumps(r,indent=2))
print('M24_SURFACE_BINDING',r)
