import bpy,json,math
from pathlib import Path
from collections import Counter
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930'
auth=json.loads((S/'authoring.json').read_text());names=sum([auth['static'][k]['objects'] for k in ('vertical','flashlight')],[])
bpy.ops.wm.open_mainfile(filepath=str(S/'HK416_Original_Editable.blend'))
report={'objects':{},'materials':{}}
for name in names:
    ob=bpy.data.objects[name];mesh=ob.data;uvs=[]
    for layer in mesh.uv_layers:
        points=[v.uv for v in layer.data]
        uvs.append({'name':layer.name,'active_render':layer.active_render,'min':[min(p[a] for p in points) for a in (0,1)],'max':[max(p[a] for p in points) for a in (0,1)],'tile_loop_count':{str(k):v for k,v in Counter((math.floor(p.x),math.floor(p.y)) for p in points).items()}})
    report['objects'][name]={'uvs':uvs,'active_index':mesh.uv_layers.active_index,'materials':[m.name for m in mesh.materials],'face_materials':dict(Counter(f.material_index for f in mesh.polygons))}
    for mat in mesh.materials:
        report['materials'][mat.name]=[{'node':n.name,'image':n.image.filepath if n.image else None} for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'] if mat.use_nodes else []
(O/'source_uv_materials.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
