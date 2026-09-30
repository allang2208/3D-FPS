"""Replace only the defective copied magazine neck, in the active 201 idle frame."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;D=O.parent/'Drum46';I=json.loads((O/'interface.json').read_text());F=Matrix(I['idle_root_from_mag'])
bpy.ops.wm.open_mainfile(filepath=str(D/'LMG201_Drum46.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
drum=bpy.data.objects['SM_LMG201_LargeDrum'];bm=bmesh.new();bm.from_mesh(drum.data)
# Entire semantic neck/inside/collar materials are replaced, with no spatial
# slicing of the old generated shell. Keep the accepted shell and its UVs.
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index>=3],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(drum.data);bm.free()
while len(drum.data.materials)>3:drum.data.materials.pop(index=3)
cx=-.000312318+I['bind_to_idle'][0][3]
def profile(half,front,rear,r):
 points=[]
 for x,y,start in [(cx+half-r,rear-r,0),(cx-half+r,rear-r,90),(cx-half+r,front+r,180),(cx+half-r,front+r,270)]:
  for j in range(5):
   a=math.radians(start+90*j/4);points.append((x+r*math.cos(a),y+r*math.sin(a)))
 return points
# The top fits within the actual A40 socket inner walls in idle: front -164,
# rear -76 mm. The shoulder reaches into the retained drum saddle below it.
stations=[(-.0505,.0194,-.1652,-.0820,.0020),
          (-.0355,.0194,-.1652,-.0820,.0020),
          (-.0325,.0180,-.1635,-.0770,.0017),
          (-.0140,.0174,-.1633,-.0768,.0015),
          (-.0040,.0174,-.1633,-.0768,.0015)]
verts=[];faces=[];roles=[];n=20
for z,half,front,rear,r in stations:verts.extend((x,y,z) for x,y in profile(half,front,rear,r))
for k in range(len(stations)-1):
 for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j));roles.append(1 if k<2 else 0)
faces.append(tuple(reversed(range(n))));roles.append(1)
# A closed recessed interior remains visible during the accepted free drop.
# It is a wall with a real floor; neither missing triangles nor a two-sided cap.
inner=profile(.0159,-.1618,-.0783,.0010);top=(len(stations)-1)*n;start=len(verts)
verts.extend((x,y,-.0040) for x,y in inner);floor=len(verts);verts.extend((x,y,-.0102) for x,y in inner)
for j in range(n):
 q=(j+1)%n;faces.extend([(top+j,top+q,start+q,start+j),(start+j,start+q,floor+q,floor+j)]);roles.extend([0,2])
faces.append(tuple(floor+j for j in range(n)));roles.append(2)
me=bpy.data.meshes.new('D47_ClosedAdapter');me.from_pydata(verts,[],faces);me.update();neck=bpy.data.objects.new('D47_ClosedAdapter',me);bpy.context.collection.objects.link(neck)
for name in ['D47_AdapterCoat','D47_ShoulderPolymer','D47_RecessInside']:
 m=bpy.data.materials.new(name);m.use_nodes=True;node=next(v for v in m.node_tree.nodes if v.type=='BSDF_PRINCIPLED')
 node.inputs['Base Color'].default_value=(.0175,.021,.0255,1) if 'Coat' in name else (.010,.013,.016,1)
 node.inputs['Metallic'].default_value=.68 if 'Coat' in name else 0;node.inputs['Roughness'].default_value=.385 if 'Coat' in name else .46;me.materials.append(m)
for p,i in zip(me.polygons,roles):p.material_index=i
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
bpy.ops.object.select_all(action='DESELECT');neck.select_set(True);bpy.context.view_layer.objects.active=neck
bev=neck.modifiers.new('Small hard surface edge radius','BEVEL');bev.width=.00035;bev.segments=3;bev.limit_method='ANGLE';bev.angle_limit=math.radians(26);bpy.ops.object.modifier_apply(modifier=bev.name)
tri=neck.modifiers.new('Deterministic triangulation for export tangents','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
for p in me.polygons:p.use_smooth=True
normal=neck.modifiers.new('Area weighted flat panel normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=50;bpy.ops.object.modifier_apply(modifier=normal.name)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(70),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT');me.uv_layers[0].name='UV0'
bm=bmesh.new();bm.from_mesh(me);joint_boundary=sum(e.is_boundary for e in bm.edges);bm.free()
neck.data.transform(F.inverted());neck['fit_frame']='Active 201 base idle; inverse mapped to unchanged magazine bone'
neck['upper_seat_depth_mm']=7.5;neck['recess_depth_mm']=6.2
bpy.ops.object.select_all(action='DESELECT');neck.select_set(True);drum.select_set(True);bpy.context.view_layer.objects.active=drum;bpy.ops.object.join()
drum=bpy.context.object;drum.name='SM_LMG201_LargeDrum';drum['revision']='DrumJoint47: closed smooth adapter; original donor shell, contact frame and animations retained'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_DrumJoint47.blend'))
path=O/'SM_LMG201_LargeDrum.fbx';bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
drum.data.calc_loop_triangles();report={'mesh':str(path),'source_blend':str(O/'LMG201_DrumJoint47.blend'),'triangles':len(drum.data.loop_triangles),'slots':[m.name for m in drum.data.materials],'joint_boundary_edges':joint_boundary,'fit_stations_idle_m':stations,'upper_seat_depth_mm':7.5,'shell_moved':False,'animation_changed':False,'runtime_tested':False}
(O/'model.json').write_text(json.dumps(report,indent=2));print('D47_MODEL_SAVED',json.dumps(report),flush=True)
