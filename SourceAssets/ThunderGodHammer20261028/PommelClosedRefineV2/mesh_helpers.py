def make(name,verts,faces,mat,bevel=0,uvs=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat);parts.append(o)
 uv=me.uv_layers.new(name=src.uv_layers[0].name)
 for p in me.polygons:
  axis=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3) if k!=axis]
  for li in p.loop_indices:
   vi=me.loops[li].vertex_index;co=me.vertices[vi].co;uv.data[li].uv=uvs[vi] if uvs else (co[axes[0]]*24,co[axes[1]]*24)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-10)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(me);bm.free()
 if bevel:finish_bevel(o,bevel)
 return o
def finish_bevel(o,width):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 mod=o.modifiers.new('Physical machined edge radius','BEVEL');mod.width=width;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(32);mod.use_clamp_overlap=True
 if o.name.startswith('Continuous structural body'):
  bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update();weights=bm.edges.layers.float.new('bevel_weight_edge')
  for e in bm.edges:e[weights]=1. if len(e.link_faces)==2 and e.calc_face_angle()>math.radians(32) and all(v.co.z<-.0263 for v in e.verts) else 0.
  bm.to_mesh(o.data);bm.free();mod.limit_method='WEIGHT'
 bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in o.data.polygons:p.use_smooth=True
 mod=o.modifiers.new('Preserved flat faces and rounded highlights','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=75;bpy.ops.object.modifier_apply(modifier=mod.name)
