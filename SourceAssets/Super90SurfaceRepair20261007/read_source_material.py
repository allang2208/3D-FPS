import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'BenelliM4_Original_Editable.blend'))
out={}
for name in ['TTI_Benelli_M4','12gauge','matchsaverz','glove_hardknuckle']:
    mat=bpy.data.materials[name];nodes=[]
    for node in mat.node_tree.nodes:
        row={'name':node.name,'type':node.type,'inputs':{}}
        for socket in node.inputs:
            if hasattr(socket,'default_value'):
                v=socket.default_value
                row['inputs'][socket.name]=list(v) if hasattr(v,'__len__') and not isinstance(v,str) else v
        if hasattr(node,'image'):row['image']=node.image.filepath if node.image else None
        nodes.append(row)
    out[name]={'nodes':nodes,'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in mat.node_tree.links]}
(O/'source_material_inputs.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
