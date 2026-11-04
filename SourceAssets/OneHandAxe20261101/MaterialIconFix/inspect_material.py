"""Read the actual saved/live axe material, limited to this user's review."""
import json
from pathlib import Path
import unreal as u

P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/OneHandAxe20261101/MaterialIconFix')
ROOT='/Game/Weapons/TacticalHatchet20261101'
L=u.MaterialEditingLibrary
mesh=u.load_asset(ROOT+'/SM_TacticalHatchet')
mat=u.load_asset(ROOT+'/Materials/M_TacticalHatchet')
r={'mesh':mesh.get_path_name(),'slots':[], 'material':mat.get_path_name(), 'properties':{}, 'textures':{}, 'graph':{}}
for slot in mesh.get_editor_property('static_materials'):
    r['slots'].append({'slot':str(slot.material_slot_name),'material':slot.material_interface.get_path_name() if slot.material_interface else None})
for name in ('two_sided','used_with_nanite','used_with_skeletal_mesh','tangent_space_normal','blend_mode'):
    r['properties'][name]=str(mat.get_editor_property(name))
for role in ('BaseColor','Normal','MetalRough'):
    t=u.load_asset(ROOT+'/Textures/T_TacticalHatchet_'+role)
    r['textures'][role]={'path':t.get_path_name(),'size':[t.blueprint_get_size_x(),t.blueprint_get_size_y()]}
    for name in ('srgb','compression_settings','flip_green_channel','lod_group','never_stream'):
        r['textures'][role][name]=str(t.get_editor_property(name))
def walk(node):
    if not node or node.get_name() in r['graph']:return
    record={'class':node.get_class().get_name(),'pins':[str(n) for n in L.get_material_expression_input_names(node)]}
    r['graph'][node.get_name()]=record
    for prop in ('texture','sampler_type','const_coordinate','base_color','normal','roughness','metallic'):
        try:record[prop]=str(node.get_editor_property(prop))
        except Exception:pass
    sources=list(L.get_inputs_for_material_expression(mat,node))
    record['sources']=[s.get_name() if s else None for s in sources]
    for source in sources:walk(source)
r['outputs']={}
for name in ('MP_FRONT_MATERIAL','MP_BASE_COLOR','MP_NORMAL','MP_METALLIC','MP_ROUGHNESS'):
    node=L.get_material_property_input_node(mat,getattr(u.MaterialProperty,name))
    r['outputs'][name]=node.get_name() if node else None
    walk(node)
(P/'material_readback.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
