"""Measure the requested vest/body intersections in the actual authored mesh."""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'Integration/QualityR3'
phase=sys.argv[sys.argv.index('--')+1]
female='--female' in sys.argv
body=json.loads((P/('SourceAssets/KaitlinPlayer20261023/NativeGeometry/MHC_Kaitlin_Body.json' if female else 'SourceAssets/JasonPlayer20261003/Jason.json')).read_text(encoding='utf-8-sig'))
bp=np.asarray(body['positions']);bf=np.asarray(body['triangles'])
if not female:bf=bf[np.asarray(body['triangle_materials'])==2]
# Native UE triangles are clockwise, as used by the existing hand producers.
tree=BVHTree.FromPolygons(bp.tolist(),bf[:,::-1].tolist(),all_triangles=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'Models/01_KevlarVest.blend'))
if female:
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    data=json.loads((S/'Integration/Delivery/vest_Kaitlin_Wear.json').read_text(encoding='utf-8-sig'))
    me=bpy.data.meshes.new('ActualKaitlinCarrier');me.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in data['positions']],[],data['triangles']);me.update()
    ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
report={'scope':('Kaitlin' if female else 'Jason')+' native rest-pose vertices and face centroids; no game or animation run','objects':[]}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    p=np.array([[v.co.x*100,-v.co.y*100,v.co.z*100] for v in ob.data.vertices])
    ob.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in ob.data.loop_triangles]);probes=np.concatenate([p,p[tri].mean(axis=1)])
    distances=[];bad=[]
    for q in probes:
        near,n,i,dist=tree.find_nearest(Vector(q));signed=float(np.dot(q-np.array(near),n));distances.append(signed)
        if signed<-.1:bad.append(q.tolist())
    a=np.asarray(distances)
    report['objects'].append(dict(name=ob.name,probes=len(a),penetrating=int((a<-.1).sum()),minimum_cm=float(a.min()),p01_cm=float(np.percentile(a,1)),bad_bounds=[np.min(bad,axis=0).tolist(),np.max(bad,axis=0).tolist()] if bad else None))
report['penetrating']=sum(o['penetrating'] for o in report['objects'])
(R/f'vest-contact-{phase}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TS01_CONTACT',report['penetrating'],[(x['name'],x['penetrating'],round(x['minimum_cm'],3)) for x in report['objects'] if x['penetrating']],flush=True)
