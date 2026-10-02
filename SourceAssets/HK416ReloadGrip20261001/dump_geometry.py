"""Convert exported native geometry to UE component centimetres for authoring."""
import bpy, numpy as np
from pathlib import Path
O=Path(__file__).parent;I=O/'Inputs';C=np.diag([100.,-100.,100.])
for name in ('HK416','factory','extended','drum'):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(I/(name+'.fbx')),use_anim=False,automatic_bone_orientation=False,ignore_leaf_bones=False)
 rig=next((o for o in bpy.context.scene.objects if o.type=='ARMATURE'),None)
 names=[b.name for b in rig.data.bones] if rig else []
 bi={n:i for i,n in enumerate(names)};P=[];T=[];BI=[];BW=[];off=0
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  me=o.data;me.calc_loop_triangles();m=np.array(o.matrix_world)
  co=np.array([v.co for v in me.vertices]);co=(m[:3,:3]@co.T).T+m[:3,3];co=(C@co.T).T
  idx=np.zeros((len(co),8),np.int32);weights=np.zeros((len(co),8),np.float32);gn={g.index:g.name for g in o.vertex_groups}
  for v in me.vertices:
   ws=sorted(((g.weight,gn[g.group]) for g in v.groups if g.weight>0 and gn.get(g.group) in bi),reverse=True)[:8]
   s=sum(w for w,n in ws) or 1.
   for k,(w,n) in enumerate(ws):idx[v.index,k]=bi[n];weights[v.index,k]=w/s
  P.append(co.astype(np.float32));T.append(np.array([t.vertices[:] for t in me.loop_triangles],dtype=np.int32)[:,::-1]+off);BI.append(idx);BW.append(weights);off+=len(co)
 np.savez_compressed(I/(name+'.npz'),pos=np.concatenate(P),tris=np.concatenate(T),bone_idx=np.concatenate(BI),bone_w=np.concatenate(BW),bones=np.array(names))
 print('HK416_AUTHOR_GEOMETRY',name,off,flush=True)
