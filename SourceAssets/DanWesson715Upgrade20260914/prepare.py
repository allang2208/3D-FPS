"""Read authoring geometry, mechanical axes and the reported fire pose."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson71520260913/DanWesson715_Manny_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
r=bpy.data.objects['SK_DW715_Manny'];root=r.data.bones['WPN_root'].matrix_local;inv=root.inverted()
report={'root':[list(row) for row in root],'parts':[],'bones':{b.name:[list(row) for row in inv@b.matrix_local] for b in r.data.bones if b.name.startswith('WPN_')}}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or ob.name=='SK_Manny_Arms_Export':continue
    points=[inv@ob.matrix_world@v.co for v in ob.data.vertices]
    adj={v.index:set() for v in ob.data.vertices}
    for edge in ob.data.edges:
        a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
    remaining=set(adj);groups={g.index:g.name for g in ob.vertex_groups}
    while remaining:
        todo=[remaining.pop()];ids=set(todo)
        while todo:
            for j in adj[todo.pop()]&remaining:remaining.remove(j);ids.add(j);todo.append(j)
        row={'object':ob.name,'ids':sorted(ids),'min':[min(points[j][k] for j in ids) for k in range(3)],'max':[max(points[j][k] for j in ids) for k in range(3)],'bones':sorted({groups[g.group] for j in ids for g in ob.data.vertices[j].groups if g.weight>.001})}
        report['parts'].append(row)
        print({k:([round(x,5) for x in v] if k in ('min','max') else len(v) if k=='ids' else v) for k,v in row.items()},flush=True)
report['fire']={}
for frame in [0,1,3,10,24]:
    a=bpy.data.actions['DW715_fire'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(frame)
    G=r.pose.bones['WPN_root'].matrix;C=G.inverted()@r.pose.bones['WPN_Cylinder'].matrix
    report['fire'][frame]=[list(row) for row in C]
    print('FIRE_AXIS',frame,'cylinder_y',list(C.to_3x3()@Vector((0,1,0))),'crane',list((G.inverted()@r.pose.bones['WPN_Crane'].matrix).to_quaternion()),flush=True)
(O/'author_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DW715_INPUTS_READY',flush=True)
