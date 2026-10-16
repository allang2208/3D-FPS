"""Bake structural detail from a cleaned, deformation-matched source high mesh."""
import bpy,json,gzip,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
O=Path(__file__).parent;P=O.parents[1];out=O/'Detail';out.mkdir(exist_ok=True)
with (O/'Input/M4_stock.bin').open('rb') as f:
 h=json.loads(f.readline());nv=h['vertices'];nt=h['triangles']
 current=np.fromfile(f,'<f4',nv*3).reshape(-1,3);tris=np.fromfile(f,'<i4',nt*3).reshape(-1,3);mids=np.fromfile(f,'<i4',nt)
 normals=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3);uv=np.fromfile(f,'<f4').reshape(h['uv_sets'],nt,3,2)
with gzip.open(P/'SourceAssets/TelescopicStockSurface20261014/Inputs/M4.json.gz','rt') as f:before=np.asarray(json.load(f)['positions'])
def local(v):return np.stack((v[...,0]*.01-.012,-v[...,1]*.01,v[...,2]*.01),axis=-1)
oldpos=local(before);newpos=local(current)
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/TacticalStock_Game_Body.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
low=bpy.data.objects['TacticalStock_Game_Body'];high=bpy.data.objects['TacticalStock_Selected_High']
tree=KDTree(len(before))
for i,v in enumerate(oldpos):tree.insert(Vector(v),i)
tree.balance();original=np.asarray([tuple(v.co) for v in low.data.vertices]);deltas=[]
for v in low.data.vertices:
 _,i,d=tree.find(v.co)
 if d>.00002:raise RuntimeError('Base low does not match installed stock '+str(d))
 deltas.append(newpos[i]-oldpos[i]);v.co=Vector(newpos[i])
deltas=np.asarray(deltas);guide=KDTree(len(original))
for i,v in enumerate(original):guide.insert(Vector(v),i)
guide.balance()
for i,v in enumerate(high.data.vertices):
 neighbors=guide.find_n(v.co,4);weights=[1/(distance+.0002)**2 for _,_,distance in neighbors];total=sum(weights)
 delta=sum((Vector(deltas[j])*w for (_,j,_),w in zip(neighbors,weights)),Vector())/total
 v.co+=delta
 if i%300000==0:print('HIGH_DETAIL_TRANSFER',i,len(high.data.vertices),flush=True)
high.data.update();low.data.update()
# Remove only dense high-mesh micro burrs. The low's full mechanical geometry,
# slots, screws, ribs and pivot are never subdivided or re-generated.
bpy.ops.object.select_all(action='DESELECT');high.hide_set(False);high.hide_render=False;high.select_set(True);bpy.context.view_layer.objects.active=high
if high.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
for face in high.data.polygons:face.use_smooth=True
smooth=high.modifiers.new('Micro burr cleanup','SMOOTH');smooth.factor=.35;smooth.iterations=3
bpy.ops.object.modifier_apply(modifier=smooth.name)
# Transfer the current production low's corner normals and precise atlas before baking.
centers=newpos[tris].mean(axis=1);ct=KDTree(len(centers))
for i,p in enumerate(centers):ct.insert(Vector(p),i)
ct.balance();cn=[]
for face in low.data.polygons:
 points=[low.data.vertices[i].co for i in face.vertices];center=sum(points,Vector())/3
 _,ti,d=ct.find(center)
 if d>.00002:raise RuntimeError('Low triangle mismatch')
 permutation=[min(range(3),key=lambda j:(p-Vector(newpos[tris[ti,j]])).length_squared) for p in points]
 for li,j in zip(face.loop_indices,permutation):
  n=normals[ti,j];cn.append((float(n[0]),float(-n[1]),float(n[2])))
  low.data.uv_layers[0].data[li].uv=uv[0,ti,j]
 face.use_smooth=True
low.data.normals_split_custom_set(cn);low.data.uv_layers.active_index=0;low.data.uv_layers[0].active_render=True
low.data.materials.clear();mat=bpy.data.materials.new('StockStructuralBake');mat.use_nodes=True;low.data.materials.append(mat)
target=bpy.data.images.new('T_TelescopicStructuralDetail_R2',width=4096,height=4096,alpha=False);target.colorspace_settings.name='Non-Color'
node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=target;mat.node_tree.nodes.active=node
for ob in bpy.context.scene.objects:
 if ob not in (low,high):ob.hide_render=True;ob.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');low.hide_set(False);low.hide_render=False;high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.bake.use_selected_to_active=True;scene.render.bake.use_cage=False;scene.render.bake.cage_extrusion=.0007;scene.render.bake.max_ray_distance=.002;scene.render.bake.margin=16;scene.render.bake.normal_space='TANGENT'
print('STRUCTURAL_DETAIL_BAKE_START',flush=True)
bpy.ops.object.bake(type='NORMAL');target.file_format='PNG';target.filepath_raw=str(out/'T_TelescopicStructuralDetail_R2.png');target.save()
high.hide_set(True);high.hide_render=True;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'TelescopicStructuralDetail_Editable.blend'))
(O/'detail_recipe.json').write_text(json.dumps({'source_high_triangles':len(high.data.polygons),'low_triangles':len(low.data.polygons),'high_micro_smoothing_iterations':3,'high_micro_smoothing_factor':.35,'normal_strength':1,'texture_size':4096,'bake_target':'current production M4 body UV0/normals; M16 restored to this atlas','gameplay_tested':False},indent=2))
print('STRUCTURAL_DETAIL_BAKE_SAVED',flush=True)
