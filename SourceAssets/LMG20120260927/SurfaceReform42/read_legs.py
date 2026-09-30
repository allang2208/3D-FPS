import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True);out={}
for key in ['BipodBase','BipodLegA','BipodLegB']:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('Before_'+key+'.fbx')),use_anim=False)
 ob=next(o for o in set(bpy.data.objects)-old if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_')));me=ob.data;me.calc_loop_triangles();v=np.array([(ob.matrix_world@q.co)[:] for q in me.vertices]);f=np.array([t.vertices[:] for t in me.loop_triangles]);np.savez_compressed(O/(key+'.npz'),v=v,f=f)
 row={'bounds':[v.min(0).tolist(),v.max(0).tolist()],'sections':[]};out[key]=row
 if key=='BipodBase':continue
 for z in [-.010,-.016,-.022,-.028,-.035,-.045]:
  q=v[abs(v[:,2]-z)<.0025]
  if len(q):row['sections'].append({'z':z,'min':q.min(0).tolist(),'max':q.max(0).tolist(),'median':np.median(q,axis=0).tolist()})
(O/'leg_inputs.json').write_text(json.dumps(out,indent=2));print('S42_LEG_INPUTS',flush=True)
