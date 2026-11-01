# Join and sew only coincident construction vertices while preserving every corner UV and normal.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=factory;bpy.ops.object.join();obj=factory
obj.name='SM_ThunderGodHammer_pommel_'+KEY+'_v2';obj.data.name=obj.name
me=obj.data;bm=bmesh.new();bm.from_mesh(me);nl=bm.loops.layers.float_vector.new('AuthoredCornerNormal')
for f,p in zip(bm.faces,me.polygons):
 for l,li in zip(f.loops,p.loop_indices):l[nl]=me.corner_normals[li].vector
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-10)
boundary=[e for e in bm.edges if e.is_boundary];multi=[e for e in bm.edges if len(e.link_faces)>2]
if boundary or multi:
 diagnostic={'boundary_edges':len(boundary),'multi_face_edges':len(multi),'boundary_positions':[[list(v.co) for v in e.verts] for e in boundary[:32]]}
 (P/'construction_issue.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
 raise RuntimeError('Structural surface not closed: '+str(diagnostic)[:500])
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
normals=[]
for f in bm.faces:
 for l in f.loops:
  n=l[nl].normalized()
  if n.length<.5:n=f.normal.copy()
  if n.dot(f.normal)<-.1:n=-n
  normals.append(tuple(n))
bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=True
me.normals_split_custom_set(normals);me.calc_loop_triangles()
positions=np.array([v.co[:] for v in me.vertices])
bpy.ops.export_scene.fbx(filepath=str(E/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/(KIND+'PommelV2_Editable.blend')))
manifest={'complete':True,'id':KEY+'_pommel','mesh':obj.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'materials':[m.name for m in me.materials],'bounds_m':[positions.min(0).tolist(),positions.max(0).tolist()],'boundary_edges':0,'multi_face_edges':0,'protected_interface':'Native socket and lip UV/custom normals; exact cut boundary sewn into continuous body; middle braid strip rebuilt','location_cm':[0,0,-8.500000089406967],'method':'Continuous solid surface with blind recessed relief, physically closed terminals, sewn native neck and precision woven collar','normal_convention':'OpenGL; UE flip green','runtime_tested':False}
(P/'model_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(KIND+'_CLOSED_V2_EXPORTED',manifest['triangles'],flush=True)
