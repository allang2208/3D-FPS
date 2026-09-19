import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
report={}
for source in ['trellis','hunyuan']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 path=P/'trellis_fixed.glb' if source=='trellis' else P.parents[1]/'Saved/Hunyuan3D/Candidates/prism_handstop_v01/asset_01.glb'
 bpy.ops.import_scene.gltf(filepath=str(path))
 o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 original_tris=sum(len(p.vertices)-2 for p in o.data.polygons)
 print(source,'loaded',original_tris,flush=True)
 if source=='hunyuan':
  bm=bmesh.new();bm.from_mesh(o.data)
  left=min(v.co.x for v in bm.verts);right=max(v.co.x for v in bm.verts)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x>left+(right-left)*.43],context='VERTS')
  bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 print(source,'welded',flush=True)
 # Orient both broad sides toward the same camera; normalize height only.
 xyz=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',xyz);xyz=xyz.reshape(-1,3)
 if source=='trellis':xyz=xyz[:,[1,0,2]].copy();xyz[:,0]*=-1
 else:xyz[:,:2]*=-1
 lo=xyz.min(axis=0);hi=xyz.max(axis=0);xyz=(xyz-(lo+hi)*.5)/(hi[2]-lo[2]);o.data.vertices.foreach_set('co',xyz.ravel())
 o.data.update()
 bpy.context.view_layer.update()
 # Ignore imported textures and custom normals in both geometry comparisons.
 if o.data.has_custom_normals:
  try:bpy.ops.mesh.customdata_custom_splitnormals_clear()
  except Exception:pass
 o.data.materials.clear();m=bpy.data.materials.new('Shared neutral surface');m.use_nodes=True
 n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(.18,.18,.18,1);n.inputs['Roughness'].default_value=.6;n.inputs['Metallic'].default_value=0;o.data.materials.append(m)
 o.data.polygons.foreach_set('material_index',np.zeros(len(o.data.polygons),dtype=np.int32));o.data.polygons.foreach_set('use_smooth',np.ones(len(o.data.polygons),dtype=bool))
 def stats():
  o.data.calc_loop_triangles()
  return {'triangles':len(o.data.loop_triangles),'vertices':len(o.data.vertices)}
 report[source]={'file_triangles':original_tris,'raw':stats(),'normalized_dimensions':list(o.dimensions)}
 print(source,'stats ready',report[source],flush=True)
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100
 s.world=bpy.data.worlds.new('Shared studio');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.1,.1,.1,1)
 def aim(a):a.rotation_euler=(-a.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.55;s.camera=cam
 for pos,power in [((-2,-3,4),400),((3,-2,1),200),((1,3,3),500)]:
  bpy.ops.object.light_add(type='AREA',location=pos);a=bpy.context.object;a.data.energy=power;a.data.size=3;aim(a)
 def render(stage):
  for view,pos in [('side',(0,-4,0)),('beauty',(2,-4,1.4)),('front',(4,0,0)),('back',(0,4,0))]:
   cam.location=pos;aim(cam);s.render.filepath=str(P/f'{source}_{stage}_{view}.png');bpy.ops.render.render(write_still=True)
 render('raw')
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 if source=='trellis':
  # Raw topology stalls the weld operation. Use the prior 5080 workflow's
  # voxel consolidation before decimation, and record this preprocessing.
  rem=o.modifiers.new('Consolidate generated surface','REMESH');rem.mode='SHARP';rem.octree_depth=8;rem.scale=.9;rem.use_remove_disconnected=True;rem.threshold=.01
  bpy.ops.object.modifier_apply(modifier=rem.name);report[source]['reduction_preprocess']='Sharp octree remesh depth 8; voxel reduction first attempt failed'
  bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);islands=[]
  while remaining:
   start=remaining.pop();group=[start];stack=[start]
   while stack:
    v=stack.pop()
    for e in v.link_edges:
     other=e.other_vert(v)
     if other in remaining:remaining.remove(other);stack.append(other);group.append(other)
   islands.append(group)
  largest=max(islands,key=len);discard=[v for group in islands if group is not largest for v in group]
  report[source]['removed_small_islands']=len(islands)-1
  if discard:bmesh.ops.delete(bm,geom=discard,context='VERTS')
  bm.to_mesh(o.data);bm.free()
 o.data.calc_loop_triangles()
 d=o.modifiers.new('Equal budget decimation','DECIMATE');d.ratio=min(1,16000/max(1,len(o.data.loop_triangles)));d.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=d.name)
 report[source]['reduced']=stats()
 bpy.ops.wm.save_as_mainfile(filepath=str(P/f'{source}_comparison.blend'))
 bpy.ops.export_scene.gltf(filepath=str(P/f'{source}_reduced.glb'),use_selection=True,export_apply=True)
 render('reduced')
(P/'comparison.json').write_text(json.dumps(report,indent=2))
print('PRISM_COMPARE_PASS',json.dumps(report))
