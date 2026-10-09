"""Task-scoped source diagnosis: guide contact and arms crossing gun surfaces."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;O.mkdir(exist_ok=True)
author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
rest=s['rest'];rig=s['rig']
body=bpy.data.objects['Super90_body'];body.data.calc_loop_triangles()
vertices=[body.matrix_world@v.co for v in body.data.vertices]
faces=[tuple(t.vertices) for t in body.data.loop_triangles]
bvh=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
report={'meshes':[],'bones':{},'surface_samples':[],'poses':[]}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    if ob.name.startswith(('Super90_','12g_')):
        vs=[ob.matrix_world@v.co for v in ob.data.vertices]
        report['meshes'].append({'name':ob.name,'vertices':len(vs),
          'lo':[min(v[k] for v in vs) for k in range(3)],'hi':[max(v[k] for v in vs) for k in range(3)]})
for n in rest:
    if any(k in n for k in ('arm','clavicle','hand','WPN_Load','WPN_root')):
        report['bones'][n]={'parent':s['parents'][n],'rest':list(rest[n].translation),'idle':list(s['idle'][n].translation)}
# Ray along native up to the underside, through the four proposed mating edges.
for x in (-.022,-.017,-.014,0,.014,.017,.022):
    for y in (-.075,-.060,-.040,-.020,0.,.009):
        loc,normal,index,distance=bvh.ray_cast(Vector((x,y,-.84)),Vector((0,0,1)),.12)
        report['surface_samples'].append({'x':x,'y':y,'z':loc.z if loc else None,'normal':list(normal) if normal else None})
arms=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Super90_V7_')]
for f in (0,14,42,75,87,104,114,122,130,138,146):
    p,handle,tube=s['pose'](f,7,False)
    for n in s['names']:
        parent=s['parents'][n]
        rig.pose.bones[n].matrix_basis=rest[n].inverted()@rest[parent]@p[parent].inverted()@p[n] if parent else rest[n].inverted()@p[n]
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    gun=body.evaluated_get(deps);me=gun.to_mesh();me.calc_loop_triangles()
    gunbvh=BVHTree.FromPolygons([gun.matrix_world@v.co for v in me.vertices],[tuple(t.vertices) for t in me.loop_triangles],all_triangles=True)
    row={'frame':f,'overlaps':{},'wrist':{}}
    for ob in arms:
        ev=ob.evaluated_get(deps);am=ev.to_mesh();am.calc_loop_triangles()
        tris=[tuple(t.vertices) for t in am.loop_triangles]
        tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in am.vertices],tris,all_triangles=True)
        ids=set(i for i,j in tree.overlap(gunbvh));dominant={}
        for i in ids:
            for vi in tris[i]:
                v=ob.data.vertices[vi]
                if not v.groups:continue
                n=ob.vertex_groups[max(v.groups,key=lambda g:g.weight).group].name
                dominant[n]=dominant.get(n,0)+1
        if ids:row['overlaps'][ob.name]={'triangles':len(ids),'weighted_bones':dominant}
        ev.to_mesh_clear()
    for side in ('l','r'):
        a,b,c=(p[k+'_'+side].translation for k in ('upperarm','lowerarm','hand'))
        neutral=p['lowerarm_'+side].to_quaternion()@rest['lowerarm_'+side].to_quaternion().inverted()@rest['hand_'+side].to_quaternion()
        dq=p['hand_'+side].to_quaternion()@neutral.inverted();axis=(c-b).normalized()
        angle=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(axis),dq.w)
        from mathutils import Quaternion
        row['wrist'][side]={'swing_degrees':math.degrees((dq@Quaternion(axis,angle).inverted()).angle),'elbow':list(b)}
    gun.to_mesh_clear();report['poses'].append(row)
    print('CONTACT_DIAG',json.dumps(row),flush=True)
target='revised_contact.json' if (O/'source_contact.json').exists() else 'source_contact.json'
(O/target).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SOURCE_CONTACT_READ',flush=True)
