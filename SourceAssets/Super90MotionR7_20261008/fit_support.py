"""Select the support-elbow plane against this gun's actual skinned surface."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
ob=bpy.data.objects['Super90_V7_M4_BareArmsV6'];ob.data.calc_loop_triangles()
rest=s['rest'];ri={n:m.inverted() for n,m in rest.items()}
weights=[[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in ob.data.vertices]
triangles=[]
for tri in ob.data.loop_triangles:
    if any(sum(w for n,w in weights[i] if n in ('upperarm_r','lowerarm_r','lowerarm_aux_r','lowerarm_twist_01_r','lowerarm_twist_02_r'))>.65 for i in tri.vertices):
        triangles.append(tuple(tri.vertices))
used=sorted(set(v for t in triangles for v in t));remap={v:i for i,v in enumerate(used)}
triangles=[tuple(remap[v] for v in t) for t in triangles]
body=bpy.data.objects['Super90_body'];body.data.calc_loop_triangles()
guntris=[tuple(t.vertices) for t in body.data.loop_triangles]
gunverts=[body.matrix_world@v.co for v in body.data.vertices]
rows=[]
for dx,dz in ((dx,dz) for dx in (0.,.015,.030) for dz in (-.060,-.070,-.080)):
 for angle in range(20,71,5):
    offset=[dx,0.,dz]
    s['support_fit']['right_pole_degrees']=angle;s['support_fit']['shoulder_offset_m']=offset
    counts=[];swing=[]
    for f in (42,87,114,122):
        p,_,_=s['pose'](f,7,False)
        matrices={n:p[n]@ri[n] for n in rest}
        verts=[sum((matrices[n]@ob.data.vertices[i].co*w for n,w in weights[i]),Vector()) for i in used]
        tree=BVHTree.FromPolygons(verts,triangles,all_triangles=True)
        move=p['WPN_root']@s['R0'].inverted()
        gun=BVHTree.FromPolygons([move@v for v in gunverts],guntris,all_triangles=True)
        counts.append(len(set(i for i,j in tree.overlap(gun))))
        lower=p['lowerarm_r'];hand=p['hand_r'];axis=(hand.translation-lower.translation).normalized()
        neutral=lower.to_quaternion()@rest['lowerarm_r'].to_quaternion().inverted()@rest['hand_r'].to_quaternion()
        dq=hand.to_quaternion()@neutral.inverted()
        twist=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(axis),dq.w)
        q=dq@Quaternion(axis,twist).inverted()
        swing.append(math.degrees(2*math.acos(min(1.,abs(q.w)))))
    cost=sum(counts)*15+sum(max(0.,v-42)**2 for v in swing)+abs(angle)*.25+Vector(offset).length*1800
    rows.append({'angle':angle,'offset':offset,'counts':counts,'wrist_swing':swing,'cost':cost})
best=min(rows,key=lambda r:r['cost'])
result={'right_pole_degrees':best['angle'],'shoulder_offset_m':best['offset'],'method':'Gun surface clearance with fixed right palm, exact bone lengths and bounded wrist swing','selected':best,'candidates':rows}
(O/'support_fit.json').write_text(json.dumps(result,indent=2))
print('SUPPORT_FIT_SELECTED',json.dumps(best),flush=True)
