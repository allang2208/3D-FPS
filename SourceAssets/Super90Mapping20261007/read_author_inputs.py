import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
rows={}
for file in ('BenelliM4_Original_Editable.blend','Super90_Gameplay_Editable.blend'):
    bpy.ops.wm.open_mainfile(filepath=str(S/file));data=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or not ('benelli' in ob.name.lower() or ob.name.startswith('Super90_') and not ob.name.startswith('Super90_V7_')):continue
        data.append({'object':ob.name,'uv':[{ 'name':v.name,'active_render':v.active_render,'first':[list(x.uv) for x in v.data[:4]],'bounds':[[min(x.uv[k] for x in v.data),max(x.uv[k] for x in v.data)] for k in range(2)]} for v in ob.data.uv_layers],
                     'materials':[{'name':m.name,'nodes':[{'type':n.type,'image':n.image.filepath if n.type=='TEX_IMAGE' and n.image else None,'uv_map':getattr(n,'uv_map',None)} for n in m.node_tree.nodes] if m.use_nodes else []} for m in ob.data.materials if m]})
    rows[file]=data
(O/'author_inputs.json').write_text(json.dumps(rows,indent=2))
print('SUPER90_AUTHOR_INPUTS',json.dumps(rows))
