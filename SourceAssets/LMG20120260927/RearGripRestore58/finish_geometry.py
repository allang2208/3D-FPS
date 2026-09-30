"""Clean degenerate source faces/corners flagged by the asset build."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;model=json.loads((O/'model.json').read_text())
for key,row in model['meshes'].items():
 bpy.ops.wm.open_mainfile(filepath=row['blend'],use_scripts=False);bpy.context.preferences.filepaths.save_version=0;ob=bpy.data.objects['SM_LMG201_'+row['variant']];me=ob.data;me.calc_loop_triangles()
 oldnorm=[n.vector.copy() for n in me.corner_normals];fixed_norm=0;fixed_uv=set();uv=me.uv_layers[0]
 for t in me.loop_triangles:
  a,b,c=[uv.data[i].uv for i in t.loops]
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-16:fixed_uv.add(t.polygon_index)
 bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();layers=[bm.loops.layers.float.new('R58FinishN'+c) for c in 'xyz'];uv0=bm.loops.layers.uv[0];removed=[]
 for f in bm.faces:
  if f.calc_area()<=1e-16:removed.append(f);continue
  for l,li in zip(f.loops,me.polygons[f.index].loop_indices):
   nn=oldnorm[li]
   if nn.length<.1:nn=f.normal.copy();fixed_norm+=1
   for i,layer in enumerate(layers):l[layer]=nn[i]
  if f.index in fixed_uv:
   # Only collapsed UV triangles are projected; preserve the sampled texel
   # center and every valid original UV island.
   axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))];center=sum((v.co for v in f.verts),Vector())/len(f.verts);uvcenter=sum((l[uv0].uv for l in f.loops),Vector((0,0)))/len(f.loops)
   for l in f.loops:l[uv0].uv=uvcenter+Vector(((l.vert.co[axes[0]]-center[axes[0]])/.10,(l.vert.co[axes[1]]-center[axes[1]])/.10))
 bmesh.ops.delete(bm,geom=removed,context='FACES');normals=[[l[layer] for layer in layers] for f in bm.faces for l in f.loops];bm.to_mesh(me);bm.free();me.update();me.normals_split_custom_set(normals)
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.fbx(filepath=row['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 bpy.ops.wm.save_as_mainfile(filepath=row['blend']);me.calc_loop_triangles();model['operations'][key]['triangles']=len(me.loop_triangles);model['operations'][key]['degenerate_finish']={'removed_zero_area_faces':len(removed),'corrected_zero_normals':fixed_norm,'corrected_collapsed_uv_faces':len(fixed_uv)}
 print('R58_DEGENERATE_FINISH',key,model['operations'][key]['degenerate_finish'],flush=True)
(O/'model.json').write_text(json.dumps(model,indent=2))
