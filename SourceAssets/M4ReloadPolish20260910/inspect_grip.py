import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HandMATRepair20260910/M4_Hand_MAT_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
print('MESHES',[(o.name,len(o.data.vertices)) for o in r.children if o.type=='MESH'])
a=bpy.data.actions['M4_MAT_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(80);bpy.context.view_layer.update()
print('BONEREL', {n:list((r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()@r.pose.bones[n].matrix).translation) for n in ['hand_l','thumb_03_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l']})
mesh=bpy.data.objects['SK_Manny_Arms_Export'];ids=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if mesh.vertex_groups[g.group].name.endswith('_l') and mesh.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
dep=bpy.context.evaluated_depsgraph_get();ev=mesh.evaluated_get(dep);m=ev.to_mesh();inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();points=[inv@ev.matrix_world@m.vertices[i].co for i in ids];ev.to_mesh_clear()
mag=next(o for o in r.children if o.type=='MESH' and 'Magazine' in o.name);ev=mag.evaluated_get(dep);m=ev.to_mesh();vertices=[inv@ev.matrix_world@v.co for v in m.vertices];faces=[list(p.vertices) for p in m.polygons];ev.to_mesh_clear();tree=BVHTree.FromPolygons(vertices,faces)
result={'mag_bounds':[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)],'hand_bounds':[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)]}
contacts=[]
for p in points:
 loc,n,face,dist=tree.find_nearest(p)
 if (p-loc).dot(n)<-.0003:contacts.append((dist,list(p),list(n)))
contacts.sort(reverse=True);result['inside_count']=len(contacts);result['deepest']=contacts[:12]
(O/'grip_probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
