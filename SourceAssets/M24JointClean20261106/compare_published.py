from pathlib import Path
import bpy,numpy as np,json
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
def read(path,metal):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True)
    ob=next(o for o in set(bpy.data.objects)-before if o.type=='MESH');me=ob.data;me.calc_loop_triangles()
    p=np.array([ob.matrix_world@v.co for v in me.vertices]);norm=np.array([n.vector[:] for n in me.corner_normals]);uv=np.array([l.uv[:] for l in me.uv_layers[0].data]);r={}
    for t in me.loop_triangles:
        if t.material_index!=metal or min(p[t.vertices,1])<.03:continue
        points=[tuple(q) for q in np.round(p[t.vertices],6)];r[tuple(sorted(points))]={key:(n,tex) for key,n,tex in zip(points,norm[t.loops],uv[t.loops])}
    return r,[l.name for l in me.uv_layers]
report={}
for kind in ('Native','Advanced'):
    a,ua=read(O/'Inputs'/(kind+'.fbx'),0);b,ub=read(O/'Inputs'/('Current_'+kind.lower()+'.fbx'),0)
    ns=[];uvs=[]
    for k in set(a)&set(b):
        for key,(n,t) in a[k].items():
            nn,tt=b[k][key];ns.append(float(np.degrees(np.arccos(np.clip(np.dot(n,nn),-1,1)))));uvs.append(float(np.max(np.abs(t-tt))))
    report[kind]={'common_triangles':len(set(a)&set(b)),'source_triangles':len(a),'current_triangles':len(b),'source_uv_layers':ua,'current_uv_layers':ub,'normal_difference_deg_percentiles':np.percentile(ns,[50,90,99,100]).tolist(),'uv0_difference_percentiles':np.percentile(uvs,[50,90,99,100]).tolist()}
(O/'published_diagnosis.json').write_text(json.dumps(report,indent=2));print('M24_PUBLISHED_DIAGNOSIS',report)
