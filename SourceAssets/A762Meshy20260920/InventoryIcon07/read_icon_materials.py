import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_CatalogIcon_Editable.blend'))
r={}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or not any(n in ob.name for n in ['Handguard_Closed','Ribbed','UpperReceiver','Rubber','RearShoulder']):continue
    r[ob.name]=[]
    for slot in ob.material_slots:
        m=slot.material;e={'slot':m.name if m else None}
        if m:
            e['use_nodes']=m.use_nodes;e['links']=[(l.from_node.type,l.from_socket.name,l.to_node.type,l.to_socket.name) for l in m.node_tree.links]
            e['bsdf']=[{'color':list(n.inputs['Base Color'].default_value),'metal':n.inputs['Metallic'].default_value} for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
        r[ob.name].append(e)
(O/'icon_materials.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
