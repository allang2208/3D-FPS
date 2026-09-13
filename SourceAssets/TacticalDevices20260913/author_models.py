import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0

def bounds(ob):
 vs=[v.co for v in ob.data.vertices]
 return Vector([min(v[i] for v in vs) for i in range(3)]),Vector([max(v[i] for v in vs) for i in range(3)])

def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

report=json.loads((O/'authoring.json').read_text()) if (O/'authoring.json').exists() else {}
selected=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else ''
for family in ['M4','AKM','QBZ191']:
 for kind,seed,length in [('laser',91803,.085),('flashlight',91827,.120)]:
  if selected and kind!=selected:continue
  bpy.ops.wm.open_mainfile(filepath=str(S/'PhantomRearGripSeamFit20260913'/(family+'_Assembly_Editable.blend')))
  names={'M4':['Receiver_M4_Handguard Kmode Unreal_Export'],'AKM':['Receiver_AKM_Soviet_Native'],'QBZ191':['Receiver_QBZ_Handguard']}[family]
  vertices=[];faces=[]
  for name in names:
   gun=bpy.data.objects[name];offset=len(vertices);vertices.extend([gun.matrix_world@v.co for v in gun.data.vertices]);faces.extend([[offset+i for i in p.vertices] for p in gun.data.polygons])
  surface=BVHTree.FromPolygons(vertices,faces)
  # Rail shoe situated on each source handguard's side, away from the support palm.
  cy,cz={'M4':(-.320,.078),'AKM':(-.310,.057),'QBZ191':(-.292,.070)}[family]
  inner=[];ny,nz=12,6
  for iz in range(nz+1):
   for iy in range(ny+1):
    y=cy+(iy/ny-.5)*.038;z=cz+(iz/nz-.5)*.018
    hit,normal,_,_=surface.ray_cast(Vector((.15,y,z)),Vector((-1,0,0)),.15)
    inner.append(Vector((hit.x-.0004 if hit is not None else float('nan'),y,z)))
  solid=[v for v in inner if math.isfinite(v.x)]
  if not solid:raise RuntimeError('No solid mounting surface '+family)
  for v in inner:
   if not math.isfinite(v.x):v.x=min(solid,key=lambda q:(q.y-v.y)**2+(q.z-v.z)**2).x
  mountx=max(v.x for v in inner)+.002
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.gltf(filepath=str(O/kind/f'seed_{seed}'/'textured_master_00001_.glb'))
  ob=next(x for x in bpy.context.scene.objects if x.type=='MESH');ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);ob.parent=None
  # TRELLIS candidates may choose different principal axes. Resolve the front
  # from the optical texture before moving the clamp onto the receiver side.
  lo0,hi0=bounds(ob);axis=max(range(2),key=lambda i:hi0[i]-lo0[i])
  material=ob.data.materials[0];shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  image=next(n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==shader.inputs['Base Color'] for l in n.outputs['Color'].links))
  w,h=image.size;pixels=np.empty(w*h*4,np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(h,w,4);optical_positions=[]
  for face in list(ob.data.polygons)[::8]:
   li=face.loop_start;uv=ob.data.uv_layers[0].data[li].uv;c=pixels[min(h-1,max(0,int(uv.y*h))),min(w-1,max(0,int(uv.x*w)))][:3]
   optical=(c[0]>.15 and c[0]>c[1]*1.8 and c[0]>c[2]*1.8) if kind=='laser' else min(c)>.4
   if optical:optical_positions.append(ob.data.vertices[ob.data.loops[li].vertex_index].co[axis])
  center=(lo0[axis]+hi0[axis])*.5
  positive=(sum(optical_positions)/len(optical_positions)>center) if optical_positions else axis==0
  rz=(-math.pi/2 if positive else math.pi/2) if axis==0 else (math.pi if positive else 0.)
  del pixels
  print('OPTICAL_AXIS',family,kind,axis,positive,len(optical_positions),flush=True)
  ob.data.transform(Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(rz,4,'Z'))
  lo,hi=bounds(ob);scale=length/(hi.y-lo.y)
  ob.data.transform(Matrix.Scale(scale,4));lo,hi=bounds(ob)
  ob.data.transform(Matrix.Translation(Vector((mountx-lo.x,cy-(lo.y+hi.y)*.5,cz-(lo.z+hi.z)*.5))))
  select(ob);ob.data.calc_loop_triangles();dec=ob.modifiers.new('Game mesh reduction','DECIMATE');dec.ratio=min(1.,35000/len(ob.data.loop_triangles));dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
  ob.name='SM_TacticalDevice';mat=ob.data.materials[0];mat.name='M_Tactical_'+kind
  bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  base=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links))
  packed=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image!=base)
  if family=='M4':
   for name,img in [('BaseColor',base),('MetalRough',packed)]:img.filepath_raw=str(O/kind/('T_'+kind+'_'+name+'.png'));img.file_format='PNG';img.save()
  lo,hi=bounds(ob)
  # Independent optical/rubber regions; do not derive semantics from generated metallic.
  for a in list(ob.data.color_attributes):ob.data.color_attributes.remove(a)
  colors=ob.data.color_attributes.new(name='MetalRegion',type='BYTE_COLOR',domain='CORNER');ob.data.color_attributes.active_color=colors
  front=[v.co for v in ob.data.vertices if v.co.y<lo.y+.003]
  emitter=Vector(((min(v.x for v in front)+max(v.x for v in front))*.5,lo.y-.001,(min(v.z for v in front)+max(v.z for v in front))*.5))
  for p in ob.data.polygons:
   for li in p.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co
    optical=v.y<lo.y+.0045 and (Vector((v.x,v.z))-Vector((emitter.x,emitter.z))).length<(hi.z-lo.z)*.36
    rubber=v.y>hi.y-.006
    c=0. if optical or rubber else 1.;colors.data[li].color=(c,c,c,1)
  # Closed saddle spans the original vent openings without filling the rifle itself.
  device_surface=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons])
  outer=[]
  for v in inner:
   contact,_,_,_=device_surface.ray_cast(Vector((0,v.y,v.z)),Vector((1,0,0)),.2)
   outer.append(Vector((contact.x+.0004 if contact is not None else mountx+.0005,v.y,v.z)))
  vs=inner+outer;count=len(inner);fs=[]
  for iz in range(nz):
   for iy in range(ny):
    a=iz*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1
    fs.extend([(d,c,b,a),(a+count,b+count,c+count,d+count)])
  edge=list(range(ny+1))+[iz*(ny+1)+ny for iz in range(1,nz+1)]+[nz*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[iz*(ny+1) for iz in range(nz-1,0,-1)]
  for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,b,b+count,a+count))
  mesh=bpy.data.meshes.new('ReceiverSaddle');mesh.from_pydata(vs,[],fs);mesh.update();mount=bpy.data.objects.new('ReceiverSaddle',mesh);bpy.context.collection.objects.link(mount)
  mount.data.materials.append(bpy.data.materials.new('M_Tactical_Collar'));uv=mount.data.uv_layers.new(name=ob.data.uv_layers[0].name)
  for p in mount.data.polygons:
   for li in p.loop_indices:
    v=mount.data.vertices[mount.data.loops[li].vertex_index].co;uv.data[li].uv=(v.y*20,v.z*20)
  col=mount.data.color_attributes.new(name='MetalRegion',type='BYTE_COLOR',domain='CORNER');mount.data.color_attributes.active_color=col
  for c in col.data:c.color=(1,1,1,1)
  select(ob);mount.select_set(True);bpy.ops.object.join()
  while len(ob.data.uv_layers)>1:ob.data.uv_layers.remove(ob.data.uv_layers[-1])
  uv=ob.data.uv_layers.new(name='ReceiverCoating');tile=(.12,.05 if family=='M4' else .025)
  for p in ob.data.polygons:
   axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(p.normal[j]))]
   for li in p.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/tile[0],v[axes[1]]/tile[1])
  ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
  out=O/family/kind;out.mkdir(parents=True,exist_ok=True)
  for name,pos in [('Emitter',emitter),('AimGuide',emitter+Vector((0,-.03,0)))]:
   e=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(e);e.parent=ob;e.location=pos;e.select_set(True)
  bpy.ops.export_scene.fbx(filepath=str(out/'SM_TacticalDevice.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
  bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'Editable.blend'))
  report[family+'_'+kind]={'family':family,'kind':kind,'fbx':str(out/'SM_TacticalDevice.fbx'),'mesh_name':ob.name,'uv_index':1,'tile_metres':tile,'slots':[m.name for m in ob.data.materials],'emitter_blender_m':list(emitter),'saddle_center_m':[mountx,cy,cz],'source_seed':seed}
  (O/'authoring.json').write_text(json.dumps(report,indent=2));print('TACTICAL_AUTHORED',family,kind,flush=True)
