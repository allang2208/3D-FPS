"""Restore opaque collars, extend their source PBR bakes, preserve rig/UV/aim."""
import bpy,bmesh,json,shutil,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;T=O/'Textures';E=O/'Exports'
T.mkdir(exist_ok=True);E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
report={'meshes':[],'textures':[],'source_checks':[],'game_tested':False}

def backup(path):
 dst=O/'Before'/path.relative_to(S)
 if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)

def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]

def partition(ob,X):
 me=ob.data;parent=list(range(len(me.vertices)))
 def root(i):
  while i!=parent[i]:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for edge in me.edges:parent[root(edge.vertices[1])]=root(edge.vertices[0])
 groups={}
 for f in me.polygons:groups.setdefault(root(f.vertices[0]),[]).append(f.index)
 me.calc_loop_triangles();tris={}
 for tri in me.loop_triangles:tris.setdefault(root(tri.vertices[0]),[]).append(tri)
 rings=[];glass=[];details=[]
 for key,faces in groups.items():
  vertices={v for f in faces for v in me.polygons[f].vertices};ps=[X@me.vertices[v].co for v in vertices]
  cx=(min(p.x for p in ps)+max(p.x for p in ps))*.5;cz=(min(p.z for p in ps)+max(p.z for p in ps))*.5
  covers=False
  for tri in tris[key]:
   p=[X@me.vertices[v].co for v in tri.vertices]
   signs=[(b.x-a.x)*(cz-a.z)-(b.z-a.z)*(cx-a.x) for a,b in zip(p,p[1:]+p[:1])]
   area=(p[1].x-p[0].x)*(p[2].z-p[0].z)-(p[1].z-p[0].z)*(p[2].x-p[0].x)
   if abs(area)>1e-12 and (min(signs)>=-1e-12 or max(signs)<=1e-12):covers=True
  (glass if covers else rings).extend(faces)
  details.append({'faces':len(faces),'axis_covered':covers,'center_y':sum(p.y for p in ps)/len(ps)})
 if len(rings)!=340 or len(glass)!=15:raise RuntimeError('Unexpected PSO partition '+str(details))
 return rings,glass,details

def fingerprint(me):
 # Material partition is the only mesh-data edit. Raw positions, skin, loops,
 # authored split normals and UV coordinates must remain byte-identical.
 data=repr(([(tuple(v.co),[(g.group,g.weight) for g in v.groups]) for v in me.vertices],
  [tuple(p.vertices) for p in me.polygons],[[tuple(d.uv) for d in uv.data] for uv in me.uv_layers],
  [tuple(n.vector) for n in me.corner_normals])).encode()
 return hashlib.sha256(data).hexdigest()

def restore(ob,body,X,label):
 before=fingerprint(ob.data);rings,glass,detail=partition(ob,X)
 mat=body.data.materials[0];slot=next((i for i,m in enumerate(ob.data.materials) if m==mat),None)
 if slot is None:ob.data.materials.append(mat);slot=len(ob.data.materials)-1
 for i in rings:ob.data.polygons[i].material_index=slot
 if fingerprint(ob.data)!=before:raise RuntimeError('Unexpected geometry/UV/normal/skin edit')
 report['source_checks'].append({'source':label,'opaque_triangles_restored':len(rings),'glass_triangles':len(glass),'geometry_uv_normal_skin_sha256':before,'unchanged':True,'islands':detail})
 return rings

def bake_rings(ob,faces,author,prefix,host=None):
 tmp=ob.copy();tmp.data=ob.data.copy();tmp.name='BAKE_PSO_Collars';bpy.context.collection.objects.link(tmp)
 world=ob.matrix_world.copy();tmp.parent=None;tmp.matrix_world=world
 for mod in list(tmp.modifiers):tmp.modifiers.remove(mod)
 bm=bmesh.new();bm.from_mesh(tmp.data);bm.faces.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in faces],context='FACES');bm.to_mesh(tmp.data);bm.free()
 if host:
  tmp.data.uv_layers[0].name='SourceUV';uv=tmp.data.uv_layers.new(name='HostCoatingUV')
  mask=tmp.data.color_attributes.new(name='PSO_CoatingRegion',type='FLOAT_COLOR',domain='CORNER')
  tile=(.12,.025) if host=='AKM' else (.05,.05) if host=='A762' else (.024,.05)
  for f in tmp.data.polygons:
   n=(world.to_3x3()@f.normal).normalized();axis=max(range(3),key=lambda k:abs(n[k]));axes=[i for i in range(3) if i!=axis]
   for li in f.loop_indices:
    p=world@tmp.data.vertices[tmp.data.loops[li].vertex_index].co
    uv.data[li].uv=(p[axes[0]]/tile[0]+.5,p[axes[1]]/tile[1]+.5);mask.data[li].color=(1,1,1,1)
  tmp.data.uv_layers.active_index=0
 tmp.data.materials.clear();tmp.data.materials.append(author)
 for f in tmp.data.polygons:f.material_index=0
 nodes=author.node_tree.nodes;links=author.node_tree.links
 out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 saved=out.inputs[0].links[0].from_socket
 if host:
  color=bs.inputs['Base Color'].links[0].from_socket
  # The retained author graph's ORM emission is the source used in author.py.
  orm=nodes['BAKE_EMISSION'].inputs['Color'].links[0].from_socket
 else:color=nodes[author['base_node']].outputs[author['base_socket']];orm=nodes[author['orm_node']].outputs[0]
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
 scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=8
 try:
  prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
  for d in prefs.devices:d.use=d.type=='OPTIX'
  if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
 except Exception:scene.cycles.device='CPU'
 for kind,value in [('BaseColor',color),('ORM',orm)]:
  src=S/('PSO1Russian20260923' if host else 'SVDSurface20260923')/'Textures'/(prefix+'_'+kind+'.png')
  dst=T/src.name;shutil.copy2(src,dst)
  im=bpy.data.images.load(str(dst),check_existing=False);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
  target=nodes.get('BAKE_TARGET') or nodes.new('ShaderNodeTexImage');target.name='BAKE_TARGET';target.image=im;nodes.active=target
  emit=nodes.get('REPAIR_EMIT') or nodes.new('ShaderNodeEmission');emit.name='REPAIR_EMIT'
  links.new(value,emit.inputs['Color']);links.new(emit.outputs[0],out.inputs[0])
  select([tmp]);tmp.hide_render=False;bpy.ops.object.bake(type='EMIT')
  im.filepath_raw=str(dst);im.file_format='PNG';im.save()
  report['textures'].append({'source':str(src),'result':str(dst),'kind':kind,'host':host or 'SVD'})
  print('PSO_COLLAR_BAKED',host or 'SVD',kind,flush=True)
 links.new(saved,out.inputs[0]);bpy.data.objects.remove(tmp,do_unlink=True)

svd=S/'SVDMatteDetail20260923'
for family in ['MatteDetail','base','vertical','canted','prism','angled']:
 path=svd/('SVD_'+family+'_Editable.blend');backup(path);bpy.ops.wm.open_mainfile(filepath=str(path))
 rig=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SM_SVD_ScopeLens'];body=bpy.data.objects['SM_SVD_ScopeBody']
 X=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()@ob.matrix_world
 faces=restore(ob,body,X,str(path))
 if family=='MatteDetail':
  with bpy.data.libraries.load(str(S/'SVDSurface20260923/SVD_Surface_Editable.blend'),link=False) as (src,dst):dst.materials=['AUTH_SVD_pso_Scope']
  author=dst.materials[0];bake_rings(ob,faces,author,'T_SVD_Surface_pso')
  # Export the same mesh set used by the current matte-detail asset.
  rig.data.pose_position='REST';bpy.context.view_layer.update()
  obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_SVD_') or o.name=='SK_Manny_Arms_Export')]+[rig]
  select(obs);bpy.context.view_layer.objects.active=rig
  export=E/'SK_SVD_Modular.fbx'
  bpy.ops.export_scene.fbx(filepath=str(export),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
  rig.data.pose_position='POSE';bpy.context.scene.frame_set(0)
  report['meshes'].append({'host':'SVD','fbx':str(export),'asset':'/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular'})
 for im in bpy.data.images:
  if im.filepath and Path(im.filepath).name.startswith('T_SVD_Surface_pso_'):im.filepath=str(T/Path(im.filepath).name)
 bpy.ops.wm.save_as_mainfile(filepath=str(path))

for host in ['AKM','A762','PKM']:
 path=S/'PSO1Russian20260923'/('PSO1_'+host+'_Editable.blend');backup(path);bpy.ops.wm.open_mainfile(filepath=str(path))
 ob=bpy.data.objects['PSO_ScopeLens'];body=bpy.data.objects['PSO_ScopeBody']
 faces=restore(ob,body,ob.matrix_world,str(path));ob.data.uv_layers[0].name='SourceUV'
 for im in bpy.data.images:
  if im.filepath and Path(im.filepath).name.startswith('T_SVD_Surface_pso_'):im.filepath=str(T/Path(im.filepath).name);im.reload()
 bake_rings(ob,faces,bpy.data.materials['AUTHOR_PSO1_'+host],'T_PSO1_'+host,host)
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
 transforms={o:o.matrix_world.copy() for o in obs}
 for o in obs:o.matrix_world=Matrix.Identity(4)
 select(obs);export=E/('SM_PSO1_'+host+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(export),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 for o,x in transforms.items():o.matrix_world=x
 for im in bpy.data.images:
  if im.filepath and Path(im.filepath).name.startswith('T_PSO1_'+host+'_'):im.filepath=str(T/Path(im.filepath).name)
 bpy.ops.wm.save_as_mainfile(filepath=str(path))
 report['meshes'].append({'host':host,'fbx':str(export),'asset':'/Game/Weapons/PSO1Russian20260923/'+host+'/SM_PSO1_'+host})
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('PSO_COLLARS_AUTHORED',len(report['meshes']),flush=True)
