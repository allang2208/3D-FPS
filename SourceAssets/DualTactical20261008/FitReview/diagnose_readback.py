import bpy,json
from pathlib import Path
from mathutils import Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
O=Path(__file__).parent;m=json.loads((O/'Repaired/manifest.json').read_text());report={}
for key in ('M4-laser-1','M4-blessed_laser-1','M4-flashlight-1'):
    bpy.ops.wm.open_mainfile(filepath=str(O/'Repaired'/(key+'.blend')));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    vs=[v.co.copy() for v in ob.data.vertices];fs=[list(p.vertices) for p in ob.data.polygons];tree=BVHTree.FromPolygons(vs,fs);worst=max((tree.find_nearest(v)[3],i) for i,v in enumerate(vs))
    report[key]={'source_triangles':len(fs),'bvh_self_error_mm':worst[0]*1000}
    for label,path in [('exported',m[key]['fbx']),('saved',str(O/'SavedExport'/(key+'.fbx')))]:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=path);obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];av=[Matrix(m[key]['canonical'])@o.matrix_world@v.co for o in obs for v in o.data.vertices];kd=KDTree(len(av))
        for i,v in enumerate(av):kd.insert(v,i)
        kd.balance();error=max(kd.find(v)[2]*1000 for v in vs)
        report[key][label]={'triangles':sum(len(o.data.polygons) for o in obs),'max_nearest_vertex_mm':error}
(O/'After/readback-diagnosis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
