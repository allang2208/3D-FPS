import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;out={}
for host in ['AKM','A762','PKM']:
    bpy.ops.wm.open_mainfile(filepath=str(O/(host+'_ReceiverReference.blend')))
    vertices=[];faces=[];moving={}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        names={g.index:g.name for g in ob.vertex_groups}
        for bone in ['PKM_Cover','PKM_Tray','PKM_Charge','PKM_CarryHandle']:
            points=[v.co for v in ob.data.vertices if any(names.get(g.group)==bone and g.weight>.5 for g in v.groups)]
            if points:moving[bone]={'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)]}
        indices={v.index for v in ob.data.vertices if any(names.get(g.group)=='WPN_root' and g.weight>.9 for g in v.groups)}
        offset=len(vertices);vertices.extend([tuple(v.co) for v in ob.data.vertices])
        faces.extend([tuple(offset+i for i in p.vertices) for p in ob.data.polygons if all(i in indices for i in p.vertices)])
    bvh=BVHTree.FromPolygons(vertices,faces)
    samples=[]
    for y in [.045,.015,-.015,-.045,-.075,-.105,-.135,-.165]:
        for z in [.035,.05,.065,.08]:
            p,n,index,d=bvh.ray_cast(Vector((.2,y,z)),Vector((-1,0,0)),.4)
            if p:samples.append({'y':y,'z':z,'x':round(p.x,6),'normal_x':round(n.x,3)})
    out[host]={'contacts':samples,'moving_bounds':moving}
(O/'interfaces.json').write_text(json.dumps(out,indent=2))
print('PSO1_INTERFACE_INPUTS_SAVED')
