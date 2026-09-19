import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;S=P.parent
bpy.context.preferences.filepaths.save_version=0
def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def bounds(pts):return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
def append(path,name):
 with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
 ob=b.objects[0];bpy.context.collection.objects.link(ob);return ob
report={}
for family in ['M4','AKM','QBZ191']:
 for kind in ['balanced','phantom']:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  if kind=='phantom':
   ob=append(S/'PhantomRearGripSeamFit20260913'/family/'PhantomRearGrip_ReceiverFit_Editable.blend','SM_PhantomRearGrip')
  else:
   bpy.ops.import_scene.gltf(filepath=str(S/'BalancedRearGrip20260913/seed_91703/textured_master_00001_.glb'))
   ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'));select(ob)
   ob.data.calc_loop_triangles();dec=ob.modifiers.new('Game candidate reduction','DECIMATE');dec.ratio=min(1,50000/len(ob.data.loop_triangles));dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
   mat=ob.data.materials[0];mat.name='M_BalancedRearGrip';bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
   base=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links))
   packed=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image!=base)
   if family=='M4':
    for name,img in [('BaseColor',base),('MetalRough',packed)]:img.filepath_raw=str(P/('T_Balanced_'+name+'.png'));img.file_format='PNG';img.save()
   factory=append(S/'PhantomRearGripSeamFit20260913'/(family+'_Assembly_Editable.blend'),'FactoryMountReference')
   sl,sh=bounds([v.co for v in ob.data.vertices]);tl,th=bounds([v.co for v in factory.data.vertices]);height=sh.z-sl.z
   # The front upper block is the interface; exclude the tall rear tang.
   head=[v.co for v in ob.data.vertices if v.co.y<sl.y+(sh.y-sl.y)*.36 and v.co.z>sl.z+height*.60]
   headtop=max(v.z for v in head);sourcecenter=(min(v.y for v in head)+max(v.y for v in head))*.5
   factoryhead=[v.co for v in factory.data.vertices if v.co.z>th.z-(th.z-tl.z)*.15]
   cy=(min(v.y for v in factoryhead)+max(v.y for v in factoryhead))*.5
   scale=(th.z-tl.z)/height;width=(th.x-tl.x)/(sh.x-sl.x)
   tr=Matrix.Translation(Vector(((tl.x+th.x)/2,cy,th.z-.003)))@Matrix.Diagonal((width,scale,scale,1))@Matrix.Translation(Vector((-(sl.x+sh.x)/2,-sourcecenter,-headtop)))
   ob.data.transform(tr)
   if family=='AKM':
    for v in ob.data.vertices:v.co.z=min(v.co.z,th.z+.001)
   floor=th.z-.012
   bm=bmesh.new();bm.from_mesh(factory.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,floor),plane_no=(0,0,1),clear_inner=True)
   bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
   uv=bm.loops.layers.uv.new(ob.data.uv_layers[0].name)
   for face in bm.faces:
    axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(face.normal[j]))]
    for loop in face.loops:loop[uv].uv=(loop.vert.co[axes[0]]*10,loop.vert.co[axes[1]]*10)
   bm.to_mesh(factory.data);bm.free();factory.data.materials.clear();factory.data.materials.append(bpy.data.materials.new('M_BalancedRearGrip_Collar'))
   select(ob);factory.hide_set(False);factory.select_set(True);bpy.ops.object.join()
  # UV0 stays intact. UV1 is metric planar coating projection for the receiver tiles.
  uv=ob.data.uv_layers.new(name='ReceiverCoating');tile=(.12,.05 if family=='M4' else .025)
  for f in ob.data.polygons:
   axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
   for li in f.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/tile[0],v[axes[1]]/tile[1])
  for attr in list(ob.data.color_attributes):ob.data.color_attributes.remove(attr)
  colors=ob.data.color_attributes.new(name='MetalRegion',type='BYTE_COLOR',domain='CORNER');ob.data.color_attributes.active_color=colors
  lo,hi=bounds([v.co for v in ob.data.vertices]);bins={}
  for v in ob.data.vertices:
   b=int((v.co.z-lo.z)/(hi.z-lo.z)*79);bins[b]=min(bins.get(b,1e9),v.co.y)
  for f in ob.data.polygons:
   for li in f.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;b=int((v.z-lo.z)/(hi.z-lo.z)*79)
    # Preserve the ribbed front grasp strip as polymer, coat the skeleton frame.
    metal=kind=='phantom' and not(v.z<-.019 and v.y<bins[b]+.0045)
    if f.material_index>0:metal=True
    colors.data[li].color=(float(metal),float(metal),float(metal),1)
  ob.name='SM_BalancedRearGrip' if kind=='balanced' else 'SM_PhantomRearGrip';select(ob)
  ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
  out=P/family/kind;out.mkdir(parents=True,exist_ok=True)
  bpy.ops.export_scene.fbx(filepath=str(out/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
  bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'Editable.blend'))
  report[family+'_'+kind]={'family':family,'kind':kind,'fbx':str(out/(ob.name+'.fbx')),'mesh_name':ob.name,'uv_index':1,'tile_metres':tile,'slots':[m.name for m in ob.data.materials]}
(P/'authoring.json').write_text(json.dumps(report,indent=2));print('REAR_GRIP_AUTHORING_COMPLETE',flush=True)
