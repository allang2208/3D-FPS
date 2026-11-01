"""Read the actual Blender meshes; compare factory coverage and fitted installation rings."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;T=P.parent;M=T/'ModulesV1';rows=[]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def check(label,ok,detail=None):rows.append({'check':label,'pass':bool(ok),'detail':detail})
def geometry(obj):
    obj.data.calc_loop_triangles()
    v=np.array([tuple(obj.matrix_world@x.co) for x in obj.data.vertices])
    f=np.array([tuple(t.vertices) for t in obj.data.loop_triangles]);return v,f
def tree(v,f):return BVHTree.FromPolygons([Vector(x) for x in v],f.tolist(),all_triangles=True)
bpy.ops.wm.open_mainfile(filepath=str(T/'ThunderGodHammer_Editable.blend'))
full=bpy.data.objects['SM_ThunderGodHammer'];fv,ff=geometry(full);fulltree=tree(fv,ff)
jobs=read(M/'exports.json')['parts']+read(M/'adapted_exports.json')['parts']
with bpy.data.libraries.load(str(M/'ThunderGodHammer_SharedParts_Editable.blend'),link=False) as (a,b):
    b.objects=[j['mesh'] for j in jobs]
objects={o.name:o for o in b.objects}
for o in b.objects:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
cuts=read(M/'interfaces.json')['cuts'];interfaces=read(M/'shared_interfaces.json')
assembly_v=[];assembly_f=[];offset=0
for j in jobs:
    obj=objects[j['mesh']];v,f=geometry(obj)
    check('finite mesh '+j['mesh'],np.isfinite(v).all() and len(f)>0)
    check('UVs and assigned materials '+j['mesh'],len(obj.data.uv_layers)>0 and all(m is not None for m in obj.data.materials))
    if j['id']=='factory':
        assembly_v.extend(v);assembly_f.extend(f+offset);offset+=len(v)
        mask=np.ones(len(v),dtype=bool)
        for axis,c in cuts.values():mask&=np.abs(v[:,axis]-c)>2.e-5
        points=v[mask][::max(1,int(mask.sum())//2000)]
        d=[fulltree.find_nearest(Vector(x))[3] for x in points]
        max_mm=max(d,default=0)*1000
        check('factory surface retained '+j['slot'],max_mm<.05,{'samples':len(d),'max_distance_mm':max_mm})
    else:
        keys={'hammer_heads':['left','right'],'head_mount':['left','right','neck'],'grip':['tail','wrap'],'pommel':['tail']}[j['slot']]
        for key in keys:
            data=interfaces[key];axis=0 if key in ('left','right') else 2
            plane=[i for i in range(3) if i!=axis]
            points=v[np.abs(v[:,axis]-data['target_cut'])<2.e-5][:,plane]
            if len(points)==0:check('installation plane '+j['id']+'/'+key,False);continue
            delta=points-np.array(data['target_center']);angle=np.mod(np.arctan2(delta[:,1],delta[:,0]),2*math.pi)
            expected=np.interp(angle,np.linspace(0,2*math.pi,len(data['target_radii'])),data['target_radii'])
            radius=np.linalg.norm(delta,axis=1)
            # Surface connector vertices; exclude cap-fill vertices within the ring.
            ring=radius>.85*expected
            errors=np.abs(radius[ring]-expected[ring])*1000
            check('installation ring '+j['id']+'/'+key,bool(len(errors)) and float(np.max(errors))<2.,
                  {'vertices':len(points),'ring_vertices':len(errors),'max_error_mm':float(np.max(errors)) if len(errors) else None})
av=np.array(assembly_v);af=np.array(assembly_f);assembled=tree(av,af)
sample=fv[::max(1,len(fv)//6000)];dist=[assembled.find_nearest(Vector(x))[3] for x in sample]
check('complete original surface covered by factory assembly',max(dist)*1000<.05,{'samples':len(dist),'max_distance_mm':max(dist)*1000})
check('factory assembled bounds match full mesh',np.max(np.abs(np.ptp(av,axis=0)-np.ptp(fv,axis=0)))<1.e-5,{'full_cm':(np.ptp(fv,axis=0)*100).tolist(),'assembled_cm':(np.ptp(av,axis=0)*100).tolist()})
report={'count':len(rows),'checks':rows,'failures':[r for r in rows if not r['pass']],'source_blend_read_only':True}
(P/'geometry-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('THUNDER_GEOMETRY_RESULT '+json.dumps({'checks':len(rows),'failures':report['failures']}),flush=True)
