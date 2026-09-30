import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'SightFinish41/LMG201_SightFinish41.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;out={}
for name in ['Receiver','Handguard','PistolGrip','TriggerGuard_S41']:
 ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles();xf=root.inverted()@ob.matrix_world;v=np.array([(xf@p.co)[:] for p in me.vertices]);f=np.array([t.vertices[:] for t in me.loop_triangles]);mid=np.array([t.material_index for t in me.loop_triangles]);np.savez_compressed(O/(name+'.npz'),v=v,f=f,mid=mid)
 row={'bounds':[v.min(0).tolist(),v.max(0).tolist()],'materials':[m.name for m in me.materials]};out[name]=row
 if name!='Receiver':continue
 bv=BVHTree.FromPolygons([Vector(p) for p in v],f.tolist(),all_triangles=True);row['side_samples']=[]
 for y in [-.235,-.225,-.210,-.190,-.175,-.160,-.135,-.110,-.100,-.080,-.040,0,.035,.060,.067]:
  sample={'y':y,'z_samples':[]}
  for z in [.010,.020,.035,.050,.060,.068]:
   hits=[]
   for side in [-1,1]:
    hit=bv.ray_cast(Vector((side*.060,y,z)),Vector((-side,0,0)),.060)[0];hits.append(hit.x if hit is not None else None)
   sample['z_samples'].append([z]+hits)
  row['side_samples'].append(sample)
(O/'surface_inputs.json').write_text(json.dumps(out,indent=2));print('S42_SURFACE_INPUTS',json.dumps({k:v['bounds'] for k,v in out.items()}),flush=True)
