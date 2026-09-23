"""Complete the factory magazine interior without changing its exterior or seat."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;D=O/'Exports';D.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDHandRepair20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SM_SVD_Magazine']
X=(r.matrix_world@r.data.bones['WPN_SOCKET_Magazine'].matrix_local).inverted()@ob.matrix_world
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
# The actual top mouth is the continuous 36-edge contour at z=50.2 mm;
# open backs of embossed exterior islands are not holes in the main casing.
edges=[e for e in bm.edges if e.is_boundary and all(.0499<(X@v.co).z<.0504 for v in e.verts)]
if len(edges)!=36:raise RuntimeError('Factory mouth topology changed; do not blanket-cap boundaries')
nextv={e.link_loops[0].vert:e.link_loops[0].link_loop_next.vert for e in edges}
start=next(iter(nextv));order=[start];v=nextv[start]
while v!=start:order.append(v);v=nextv[v]
outer=[X@v.co for v in order];bm.free()
center=sum(outer,Vector())/len(outer);lo=Vector([min(v[i] for v in outer) for i in range(3)]);hi=Vector([max(v[i] for v in outer) for i in range(3)])
levels=[]
# A rolled edge, wall thickness, a visible recess and a small follower bevel.
for inset,drop in [(0.,0.),(.00025,.00005),(.00105,.00035),(.00115,.0125),(.00165,.0130)]:
 ring=[]
 for p in outer:
  q=p.copy()
  for i in range(2):q[i]=center[i]+(p[i]-center[i])*(1-2*inset/(hi[i]-lo[i]))
  q.z-=drop;ring.append(q)
 levels.append(ring)
vs=[p for ring in levels for p in ring];N=len(outer);fs=[]
for j in range(len(levels)-1):
 for i in range(N):k=(i+1)%N;fs.append((j*N+k,j*N+i,(j+1)*N+i,(j+1)*N+k))
fs.append(tuple(reversed(range((len(levels)-1)*N,len(levels)*N))))
me=bpy.data.meshes.new('SVD_MagazineMouth_ClosedInterior');me.from_pydata([X.inverted()@v for v in vs],[],fs);me.update()
inside=bpy.data.objects.new('SM_SVD_MagazineInterior',me);bpy.context.collection.objects.link(inside)
inside.parent=ob.parent;inside.matrix_parent_inverse=ob.matrix_parent_inverse.copy();inside.matrix_world=ob.matrix_world.copy()
mat=bpy.data.materials.new('SVD_InterfaceSteel');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.025,.029,.034,1);bs.inputs['Metallic'].default_value=.84;bs.inputs['Roughness'].default_value=.34
me.materials.append(mat)
uv=me.uv_layers.new(name='InteriorUV')
for face in me.polygons:
 axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
 for li in face.loop_indices:
  p=vs[me.loops[li].vertex_index];uv.data[li].uv=(p[axes[0]]/.05,p[axes[1]]/.05)
group=inside.vertex_groups.new(name='WPN_SOCKET_Magazine');group.add(list(range(len(me.vertices))),1,'REPLACE')
bpy.ops.object.select_all(action='DESELECT');inside.select_set(True);bpy.context.view_layer.objects.active=inside
mod=inside.modifiers.new('TriangulatedInterior','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
mod=inside.modifiers.new('SharedManny','ARMATURE');mod.object=r
# Export the same modular body and original skin. Only a magazine-bound interior is added.
r.data.pose_position='REST';bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_SVD_') or o.name=='SK_Manny_Arms_Export')]+[r]
for o in objects:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(D/'SK_SVD_Modular.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_MagazineComplete_Editable.blend'))
(O/'model_authoring.json').write_text(json.dumps({'source':str(S/'SVDHandRepair20260923/SVD_base_Editable.blend'),
 'runtime':'/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular','mouth_edges':N,
 'rim_thickness_mm':1.05,'follower_recess_mm':13,'changed':'mouth edge, inner walls, recessed follower; original exterior, UV0, normals, rig, mount, skin unchanged',
 'new_slot':'SVD_InterfaceSteel','material':'/Game/Weapons/SVDDragunov20260922/Accessories20260923/Materials/M_SVD_InterfaceSteel',
 'existing_dry_wet_mapping':True,'game_tested':False},indent=2))
print('SVD_MAG_MODEL_SAVED',flush=True)
