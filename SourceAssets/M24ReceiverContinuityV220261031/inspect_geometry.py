import bpy,bmesh,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_ReceiverContinuityV2_Editable.blend'),load_ui=False,use_scripts=False)
body=bpy.data.objects['M24_OnePieceLowerReceiver'];bm=bmesh.new();bm.from_mesh(body.data)
R={'receiver_vertices':len(bm.verts),'receiver_faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
remaining=set(bm.verts);sizes=[]
while remaining:
 todo=[remaining.pop()];n=0
 while todo:
  v=todo.pop();n+=1
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);todo.append(w)
 sizes.append(n)
R['receiver_component_sizes']=sorted(sizes,reverse=True);bm.free()
ring=json.loads((O/'geometry_contract.json').read_text())['hinge_ring']
verts=np.array([v.co[:] for v in body.data.vertices]);stock=np.array([v.co[:] for v in bpy.data.objects['M24_SkeletonStock_ReferenceProportion'].data.vertices])
R['stock_interface_max_ring_vertex_error_mm']=max(float(np.linalg.norm(stock-np.array(p),axis=1).min()) for p in ring)*1000
R['receiver_interface_max_ring_vertex_error_mm']=max(float(np.linalg.norm(verts-np.array(p),axis=1).min()) for p in ring)*1000
trigger=bpy.data.objects['M24_trigger'];p=np.array([v.co[:] for v in trigger.data.vertices]);R['trigger_bounds_m']=[p.min(0).tolist(),p.max(0).tolist()]
R['trigger_world_matrix']=list(map(list,trigger.matrix_world))
joined=bpy.data.objects['M24_ContinuousStockReceiver'];bm=bmesh.new();bm.from_mesh(joined.data)
R['hinge_boundary']=[[[float(c) for c in v.co] for v in e.verts] for e in bm.edges if e.is_boundary and all(abs(v.co.y+.043)<.0000003 for v in e.verts)]
bm.free()
R['images_are']='Blender source assembly previews, not UE runtime captures'
(O/'geometry_review.json').write_text(json.dumps(R,indent=2));print(json.dumps(R),flush=True)
