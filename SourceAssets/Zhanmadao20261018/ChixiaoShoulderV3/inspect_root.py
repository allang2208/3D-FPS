import json, math
from pathlib import Path
import bpy
from mathutils import Vector

P=Path(__file__).resolve().parent
V2=P.parent/'ChixiaoGripV2'
bpy.ops.wm.open_mainfile(filepath=str(V2/'Standard/Chixiao_GripV2_Editable.blend'))
scene=bpy.context.scene
vf=math.tan(math.radians(75)/2);hf=vf*16/9
surfaces=[];info=[]
for obj in scene.objects:
    if obj.type!='MESH' or not obj.vertex_groups:continue
    groups={g.index:g.name for g in obj.vertex_groups}
    counts={}
    for face in obj.data.polygons:
        for edge in face.edge_keys:counts[edge]=counts.get(edge,0)+1
    adjacency={}
    for (a,b),count in counts.items():
        if count!=1:continue
        adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    remaining=set(adjacency)
    while remaining:
        todo=[remaining.pop()];ring=set(todo)
        while todo:
            for i in adjacency[todo.pop()]:
                if i not in ring:ring.add(i);remaining.discard(i);todo.append(i)
        weights={}
        for i in ring:
            for group in obj.data.vertices[i].groups:
                name=groups[group.group];weights[name]=weights.get(name,0)+group.weight/len(ring)
        top=sorted(weights.items(),key=lambda row:-row[1])[:5]
        center=sum((obj.matrix_world@obj.data.vertices[i].co for i in ring),Vector())/len(ring)
        info.append({'object':obj.name,'count':len(ring),'rest_center':list(center),'weights':top})
        if len(ring)>12 and any(n.startswith(('clavicle_r','upperarm_r','upperarm_twist')) and n.endswith('_r') and w>.1 for n,w in top):
            surfaces.append((obj,sorted(ring)))
rows=[]
for frame in range(241):
    scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();points=[]
    for obj,indices in surfaces:
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
        points.extend(evaluated.matrix_world@mesh.vertices[i].co for i in indices)
        evaluated.to_mesh_clear()
    visible=[p for p in points if p.y>.01 and abs(p.x)<hf*p.y and abs(p.z)<vf*p.y]
    rows.append({'t':frame/240,'visible_root_vertices':len(visible),
                 'bottom_plane_max_cm':max((p.z+vf*p.y for p in points),default=0)*100,
                 'points': [list(p) for p in points]})
result={'rings':info,'selected_root_rings':len(surfaces),'frames':rows}
(P/'root-inspection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('BOUNDARY_RINGS',json.dumps(info),flush=True)
print('ROOT_EXPOSURE',json.dumps([{k:v for k,v in row.items() if k!='points'} for row in rows if row['visible_root_vertices'] and round(row['t']*240)%12==0]),flush=True)
