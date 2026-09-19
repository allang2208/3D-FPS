import bpy,json,itertools
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_MAT_equip_charge'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(18);bpy.context.view_layer.update();inv=r.pose.bones['WPN_root'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();h=bpy.data.objects['SK_Manny_Arms_Export'];body=bpy.data.objects['M4_M4 Body_Export'];stock=bpy.data.objects['M4_Stock Classic Unreal_Export']
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_r') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7};indexids=[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name=='index_03_r' and g.weight>.8 for g in v.groups)];trees=[]
for o in [body,stock,h]:
 ev=o.evaluated_get(dg);m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];fs=[list(p.vertices) for p in m.polygons if o!=h or any(i in ids for i in p.vertices)];ev.to_mesh_clear()
 if o==h:hv=vs;hf=fs
 else:
  trees.append(BVHTree.FromPolygons(vs,fs))
  if o==body:
   handleids={v.index for v in o.data.vertices if any(o.vertex_groups[g.group].name=='WPN_ChargingHandle' and g.weight>.8 for g in v.groups)};handle=BVHTree.FromPolygons(vs,[f for f in fs if any(i in handleids for i in f)])
results=[]
for dx,dy,dz in itertools.product([-.026,-.028,-.030,-.032,-.034,-.036],[-.010,-.006,-.002,.002,.006],[-.004,-.002,0,.002]):
 off=Vector((dx,dy,dz));v=[p+off for p in hv];tree=BVHTree.FromPolygons(v,hf);pairs=sum(len(tree.overlap(t)) for t in trees);dist=min(handle.find_nearest(v[i])[3] for i in indexids)*1000;results.append({'offset':[dx,dy,dz],'pairs':pairs,'index_distance_mm':dist})
results.sort(key=lambda x:(x['pairs']>0,x['index_distance_mm']+x['pairs']));(O/'hook_fit.json').write_text(json.dumps(results,indent=2));print(results[:8])
