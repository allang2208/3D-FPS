"""Export lower-arm authoring coordinates from the accepted Manny mesh without edits."""
import bpy, json
from pathlib import Path
from mathutils import Vector

OUT=Path(__file__).parent
SOURCE=OUT.parent/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
obj=bpy.data.objects['SK_Manny_Arms_Export']
rig=obj.find_armature()
to_mesh=obj.matrix_world.inverted()@rig.matrix_world
groups={g.index:g.name for g in obj.vertex_groups}
parents=list(range(len(obj.data.vertices)))
def find(i):
    while parents[i]!=i:
        parents[i]=parents[parents[i]];i=parents[i]
    return i
for edge in obj.data.edges:
    a,b=(find(i) for i in edge.vertices);parents[b]=a
gloves={r['id'] for r in json.loads((OUT/'components.json').read_text()) if r['hand']>.5}
parts={}
axes={}
for side in ('l','r'):
    elbow=to_mesh@rig.data.bones['lowerarm_'+side].head_local
    wrist=to_mesh@rig.data.bones['hand_'+side].head_local
    axis=wrist-elbow
    axes[side]=(elbow,axis,axis.length_squared)
for v in obj.data.vertices:
    parts.setdefault(find(v.index),[]).append(v)
report={'source':str(SOURCE),'mesh':obj.name,'axes':{},'components':[]}
for side,(elbow,axis,length2) in axes.items():
    report['axes'][side]={'elbow':list(elbow),'wrist':list(elbow+axis),'length_m':length2**.5}
for root,verts in parts.items():
    if root in gloves: continue
    side='l' if sum(v.co.x for v in verts)<0 else 'r'
    elbow,axis,length2=axes[side]
    ts=[(v.co-elbow).dot(axis)/length2 for v in verts]
    report['components'].append({'id':root,'vertices':len(verts),'center':list(sum((v.co for v in verts),Vector())/len(verts)),
                                  't_range':[min(ts),max(ts)]})
obj.data.calc_loop_triangles()
uv=obj.data.uv_layers.active.data
faces=[]
for tri in obj.data.loop_triangles:
    if tri.material_index!=1 or find(tri.vertices[0]) in gloves: continue
    points=[]
    for vi in tri.vertices:
        v=obj.data.vertices[vi]
        side='l' if v.co.x<0 else 'r'
        elbow,axis,length2=axes[side]
        t=(v.co-elbow).dot(axis)/length2
        inward=Vector((1,0,0)) if side=='l' else Vector((-1,0,0))
        inner=(v.normal.dot(inward)+1)*.5
        points.append([t,inner,*v.co,*v.normal])
    faces.append({'uv':[list(uv[li].uv) for li in tri.loops],'fields':points})
(OUT/'forearm_faces.json').write_text(json.dumps(faces))
(OUT/'geometry_report.json').write_text(json.dumps(report,indent=2))
print('FOREARM_GEOMETRY',json.dumps(report))
