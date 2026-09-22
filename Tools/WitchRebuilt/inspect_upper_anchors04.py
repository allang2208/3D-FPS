"""Scoped source diagnosis for the reported upper garment movement problem."""
import bpy, json
from pathlib import Path
from mathutils import Vector, geometry
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
bpy.ops.wm.open_mainfile(filepath=str(root/'Authoring/WitchRebuilt_Master.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
proxy=bpy.data.objects['WitchRebuilt_UpperSimulationProxy']
def ue(v):return Vector((v.x*100,-v.y*100,v.z*100))
def bone(name):return ue(rig.matrix_world@rig.data.bones[name].head_local)
def segment(v,a,b):
    p,t=geometry.intersect_point_line(v,a,b)
    return a if t<0 else b if t>1 else p
values=[]
for vert in proxy.data.vertices:
    v=ue(proxy.matrix_world@vert.co);side='l' if v.x>0 else 'r'
    shoulder,elbow,hand=[bone(n+'_'+side) for n in ('upperarm','lowerarm','hand')]
    p1,p2=segment(v,shoulder,elbow),segment(v,elbow,hand)
    axis=p1 if (v-p1).length_squared<(v-p2).length_squared else p2
    if (abs(v.x)<19 and v.z>138) or (v.z>shoulder.z-2 and abs(v.x)<28) or (v-hand).length<5.5:d=0
    elif abs(v.x)>22:d=min(17,max(0,(axis.z-v.z-1.5)*.7))
    else:d=min(7,max(0,(138-v.z)*.13))
    values.append(d)
neighbors=[set() for _ in values]
for edge in proxy.data.edges:
    a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
remaining=set(range(len(values)));components=[]
while remaining:
    stack=[remaining.pop()];verts=[]
    while stack:
        v=stack.pop();verts.append(v)
        for other in neighbors[v]&remaining:
            remaining.remove(other);stack.append(other)
    components.append({'vertices':len(verts),'pinned':sum(values[i]==0 for i in verts),'max_distance_cm':max(values[i] for i in verts)})
result={'vertices':len(values),'pinned':sum(v==0 for v in values),'components':sorted(components,key=lambda c:c['vertices'],reverse=True),'simulation_tested':False}
(root/'DrapeGrip20260922/upper_anchor_source.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
