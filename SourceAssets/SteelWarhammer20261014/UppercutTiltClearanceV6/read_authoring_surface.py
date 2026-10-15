"""Read the native shoulder boundary for uppercut pose authoring; no render."""
import bpy,json
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'UppercutShiftWristV5/Warhammer_Uppercut_ShiftWrist_Editable.blend'))
r=bpy.data.objects['SK_RusticPickaxe_Rig'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
out={'rings':[],'meshes':[],'poses':[]}
for ob in s.objects:
    if ob.type!='MESH' or not ob.vertex_groups:continue
    groups={g.index:g.name for g in ob.vertex_groups}
    points=[r.matrix_world.inverted()@ob.matrix_world@v.co for v in ob.data.vertices]
    weights=[{groups[g.group]:g.weight for g in v.groups if groups[g.group] in rest and g.weight>1e-6} for v in ob.data.vertices]
    out['meshes'].append({'name':ob.name,'vertices':len(points)})
    weld={};ids=[];representative={}
    for i,p in enumerate(points):
        key=tuple(round(c,5) for c in p)
        if key not in weld:weld[key]=len(weld)
        idx=weld[key];ids.append(idx);representative[idx]=i
    edges=Counter()
    for poly in ob.data.polygons:
        for a,b in poly.edge_keys:edges[tuple(sorted((ids[a],ids[b])))]+=1
    adjacency=defaultdict(set)
    for (a,b),count in edges.items():
        if count==1:adjacency[a].add(b);adjacency[b].add(a)
    remaining=set(adjacency)
    while remaining:
        stack=[remaining.pop()];ring=[]
        while stack:
            n=stack.pop();ring.append(representative[n])
            for nxt in adjacency[n]:
                if nxt in remaining:remaining.remove(nxt);stack.append(nxt)
        if len(ring)<8:continue
        summary=Counter()
        for i in ring:summary.update(weights[i])
        if not any('upperarm' in n for n,w in summary.most_common(3)):continue
        entry={'mesh':ob.name,'count':len(ring),'weights':summary.most_common(6),
               'points':[list(points[i]) for i in ring],'skin':[weights[i] for i in ring]}
        out['rings'].append(entry)
for t in (0.,1.,1.025,1.05,1.075,1.1,1.125,1.3,1.5,1.75,2.05):
    f=t*240;s.frame_set(int(f),subframe=f-int(f));pose={b.name:b.matrix.copy() for b in r.pose.bones}
    row={'t':t,'joints':{n:list(pose[n].translation) for n in ('upperarm_r','lowerarm_r','hand_r')},'rings':[]}
    for ring in out['rings']:
        pts=[]
        for point,weights in zip(ring['points'],ring['skin']):
            p=Vector(point);v=sum(((pose[n]@rest[n].inverted()@p)*w for n,w in weights.items()),Vector())/sum(weights.values());pts.append(v)
        row['rings'].append({'bounds':[[min(p[k] for p in pts),max(p[k] for p in pts)] for k in range(3)]})
    out['poses'].append(row)
out['rest']={n:[list(v) for v in m] for n,m in rest.items()}
(P/'authoring_surface.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('AUTHORING_INPUTS',json.dumps({'meshes':out['meshes'],'rings':[{k:v for k,v in x.items() if k not in ('points','skin')} for x in out['rings']],'poses':out['poses']}))
