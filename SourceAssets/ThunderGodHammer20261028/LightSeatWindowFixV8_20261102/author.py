"""Repair native degenerate edges before subtracting light-seat apertures."""
from pathlib import Path
import ast,bpy,bmesh,numpy as np,json
P=Path(__file__).resolve().parent;OLD=P.parent/'CommonSeatsStructuralV7_20261102'
CX=-.0004452141;CZ=.9095
# Reuse V7's approved aperture shape and shoulder deformation without running
# its three-variant authoring entry point or rewriting other variants.
tree=ast.parse((OLD/'author.py').read_text(encoding='utf-8'))
names={'smooth','region','seam_weight','deform','select','cutter'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(OLD/'author.py'),'exec'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent/'SeatInlaidC6/ThorSeats_InlaidC6.blend'),link=False) as(a,b):
 b.objects=['SM_ThunderGodHammer_head_mount_ribbed_light']
ob=b.objects[0];bpy.context.collection.objects.link(ob)
ob.name='SM_ThunderGodHammer_head_mount_ribbed_light_V8';ob.hide_set(False);ob.hide_render=False
mesh=ob.data;p=np.array([v.co[:] for v in mesh.vertices],np.float64)
loop_ids=np.array([l.vertex_index for l in mesh.loops])
normals=np.array([n.vector[:] for n in mesh.corner_normals],np.float64)
jac=np.empty((len(p),3,3));eps=.00002
for a in range(3):
 hi=p.copy();lo=p.copy();hi[:,a]+=eps;lo[:,a]-=eps
 jac[:,:,a]=(deform(hi,'ribbed_light')-deform(lo,'ribbed_light'))/(2*eps)
normals=np.linalg.solve(jac[loop_ids].transpose(0,2,1),normals[...,None])[...,0]
normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
mesh.vertices.foreach_set('co',deform(p,'ribbed_light').astype(np.float32).ravel());mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);layer=bm.loops.layers.float_vector.new('PreservedSourceNormal')
for face,poly in zip(bm.faces,mesh.polygons):
 for loop,li in zip(face.loops,poly.loop_indices):loop[layer]=normals[li]
# Source has collapsed triangles and four-face edges. Remove only submicron
# degeneracies before asking the solid boolean to classify inside/outside.
original_faces=len(bm.faces)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00000015)
preserved=[tuple(loop[layer]) for face in bm.faces for loop in face.loops]
repair=dict(source_faces=original_faces,repaired_faces=len(bm.faces),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges))
bm.to_mesh(mesh);bm.free();mesh.update()
for face in mesh.polygons:face.use_smooth=True
mesh.normals_split_custom_set(preserved)
with bpy.data.libraries.load(str(OLD/'ThorSeats_StructuralV7_Editable.blend'),link=False) as(a,b):
 b.materials=['M_ThorSeatV7_InnerSteel']
inner=b.materials[0];mesh.materials.append(inner)
for side in (-1,1):
 cut=cutter(side);cut.data.materials.append(mesh.materials[0]);cut.data.materials.append(inner)
 for face in cut.data.polygons:face.material_index=1
 select(ob);mod=ob.modifiers.new('WindowSolidCut_'+str(side),'BOOLEAN')
 mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
 mod.use_self=True;mod.use_hole_tolerant=True
 bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cut,do_unlink=True)
mesh=ob.data;uv=mesh.uv_layers.active.data
for face in mesh.polygons:
 if face.material_index!=1:continue
 axis=int(np.argmax(np.abs(face.normal)));axes=[i for i in range(3) if i!=axis]
 for li in face.loop_indices:
  co=mesh.vertices[mesh.loops[li].vertex_index].co
  uv[li].uv=(co[axes[0]]/.025,co[axes[1]]/.025)
 face.use_smooth=False
coords=np.array([v.co[:] for v in mesh.vertices]);mesh.calc_loop_triangles()
# The aperture construction extends to +/-90 mm; those vertices cannot be
# part of the delivered seat. This is the reported failure's production gate.
if coords[:,1].min()<p[:,1].min()-.00001 or coords[:,1].max()>p[:,1].max()+.00001:
 bpy.ops.wm.save_as_mainfile(filepath=str(P/'Unfinished_WindowRepair.blend'))
 raise RuntimeError('Boolean retained exterior cutter faces; export refused')
(P/'Export').mkdir(exist_ok=True);select(ob)
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'LightSeat_WindowFixV8_Editable.blend'))
row=dict(id='ribbed_light',mesh=ob.name,appearance='原厂三结圆徽 · 双侧贯穿减重窗 · 连续承力锻肋',triangles=len(mesh.loop_triangles),bounds_m=[coords.min(axis=0).tolist(),coords.max(axis=0).tolist()],materials={
 'M_ThorSeatC6_ribbed_light':'/Game/Weapons/ThunderGodHammer20261028/SeatInlaidC6/M_ThorSeatC6_ribbed_light.M_ThorSeatC6_ribbed_light',
 inner.name:'/Game/Weapons/ThunderGodHammer20261028/CommonSeatsStructuralV7/M_ThorSeatV7_InnerSteel.M_ThorSeatV7_InnerSteel'})
(P/'model_manifest.json').write_text(json.dumps(dict(complete=True,parts=[row],source_repair=repair,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('LIGHT_SEAT_V8_EXPORTED',json.dumps(repair),row['bounds_m'],flush=True)
