"""Restore the accepted dense source's surface without changing host interfaces."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;D=json.loads((O/'capture.json').read_text());META=json.loads((O/'current_metadata.json').read_text());OUT=O/'Exports';OUT.mkdir(exist_ok=True)
FIT=json.loads((S/'PhantomRearGripIntegration20260913/authoring.json').read_text())['fits']
HK=Matrix(json.loads((S/'HK416Reworked20260930/authoring.json').read_text())['root_matrix'])
PK=Matrix(json.loads((S/'PKMLowpoly20260922/GripMount25/authoring.json').read_text())['phantom_reargrip']['rigid_correction'])@Matrix(json.loads((S/'PKMLowpoly20260922/GripContact15/reargrips.json').read_text())['phantom_reargrip']['donor_to_root'])
S90=Matrix(json.loads((S/'Super90RearGrips20261012/models.json').read_text())['parts']['phantom_reargrip']['rigid_transform'])
BS={'M4':0,'AKM':0,'QBZ191':0,'M16':1,'HK416':0,'A762':1,'PKM':1,'Super90':0}
R={'assets':{},'complete':False,'gameplay_tested':False,'source':'Accepted seed 91627; seam weld, degenerate-edge cleanup, curvature-preserving reduction'}
def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def preserve_normals(me):
 a=me.attributes.get('PreservedNormal') or me.attributes.new('PreservedNormal','FLOAT_VECTOR','CORNER');a.data.foreach_set('vector',np.asarray([tuple(n.vector) for n in me.corner_normals],dtype=np.float32).ravel())
def restore_normals(me):
 a=me.attributes.get('PreservedNormal')
 if a:
  n=[tuple(v.vector) for v in a.data];me.normals_split_custom_set(n);me.attributes.remove(a)
def freeze(ob):
 ns=[tuple((ob.matrix_world.to_3x3().inverted().transposed()@n.vector).normalized()) for n in ob.data.corner_normals];ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.normals_split_custom_set(ns)
def transform(ob,key):
 source=np.asarray([tuple(v.co) for v in ob.data.vertices]);ns=np.asarray([tuple(n.vector) for n in ob.data.corner_normals]);li=np.asarray([l.vertex_index for l in ob.data.loops])
 family=key if key in ['M4','AKM','QBZ191'] else ('AKM' if key in ['A762','PKM'] else 'M4')
 ob.data.transform(Matrix(FIT[family]['root_space_metres']))
 dy,dz={'M4':(-.011,.012),'AKM':(-.005,.012),'QBZ191':(-.010,.011)}[family]
 for v in ob.data.vertices:
  t=max(0,min(1,(v.co.z+.045)/.030));t=t*t*(3-2*t);v.co.y+=dy*t;v.co.z+=dz*t
  if family=='M4' and v.co.z>.020:v.co.z+=.0045*max(0,min(1,(v.co.y-.008)/.014))
 if key=='M16':
  for v in ob.data.vertices:
   if v.co.z>.008:v.co.z=.008+(v.co.z-.008)*(.01657-.008)/(.03731205-.008)
 if key=='A762':
  for v in ob.data.vertices:
   y,z=v.co.y,v.co.z
   def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
   v.co.y+=.0115*smooth((.0125-z)/.0085)*smooth((z+.044)/.029)*(1-smooth((y-.004)/.032))
 if key=='PKM':ob.data.transform(PK)
 if key=='Super90':ob.data.transform(S90)
 # HK416's existing asset is in its bind frame, with a zero-height body cut in root space.
 if key=='HK416':ob.data.transform(HK)
 # Preserve the source's authored corner normals through the nonlinear neck fit.
 def pointmap(points):
  matrix=np.asarray(FIT[family]['root_space_metres']);p=points@matrix[:3,:3].T+matrix[:3,3]
  t=np.clip((p[:,2]+.045)/.030,0,1);t=t*t*(3-2*t);p[:,1]+=dy*t;p[:,2]+=dz*t
  if family=='M4':p[:,2]+=(p[:,2]>.020)*.0045*np.clip((p[:,1]-.008)/.014,0,1)
  if key=='M16':p[:,2]=np.where(p[:,2]>.008,.008+(p[:,2]-.008)*(.01657-.008)/(.03731205-.008),p[:,2])
  if key=='A762':
   def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
   p[:,1]+=.0115*smooth((.0125-p[:,2])/.0085)*smooth((p[:,2]+.044)/.029)*(1-smooth((p[:,1]-.004)/.032))
  extra={'PKM':PK,'Super90':S90,'HK416':HK}.get(key)
  if extra is not None:a=np.asarray(extra);p=p@a[:3,:3].T+a[:3,3]
  return p
 jac=np.stack([(pointmap(source+np.eye(3)[i]*1e-6)-pointmap(source-np.eye(3)[i]*1e-6))/(2e-6) for i in range(3)],axis=2)
 inv=np.linalg.inv(jac);newns=np.einsum('nij,nj->ni',np.transpose(inv,(0,2,1))[li],ns);newns/=np.maximum(np.linalg.norm(newns,axis=1,keepdims=True),1e-20);ob.data.normals_split_custom_set(newns)
 return family
def cut_body(ob,key):
 if key not in ['HK416','A762','Super90']:return
 p,n=(Vector((0,0,-.010)),Vector((0,0,1))) if key=='A762' else ((Vector((0,0,-.836)),Vector((0,0,1))) if key=='Super90' else (HK@Vector((0,0,0)),(HK.to_3x3().inverted().transposed()@Vector((0,0,1))).normalized()))
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=p,plane_no=n,clear_outer=True);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
def projected(me,tile):
 p=np.asarray([tuple(v.co) for v in me.vertices]);t=np.asarray([list(f.vertices) for f in me.polygons]);q=p[t];fn=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);axis=np.argmax(abs(fn),axis=1);uv=np.empty((len(t),3,2))
 for a in range(3):
  ids=axis==a;axes=[i for i in range(3) if i!=a];uv[ids]=q[ids][:,:,axes]/np.array(tile)
 return uv
for key,row in D['assets'].items():
 if key=='LMG201':continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.import_scene.fbx(filepath=row['export']);old=next(o for o in bpy.context.scene.objects if o.type=='MESH');freeze(old)
 body_slot=BS[key];oldme=old.data;oldbounds=np.array([tuple(v.co) for v in oldme.vertices]);before_interface=sum(f.material_index!=body_slot for f in oldme.polygons)
 # FBX exports material names, so restore slot identities before joining.
 for i,m in enumerate(oldme.materials):m.name=row['slots'][i]['name']
 oldslots=list(oldme.materials);uvnames=[u.name for u in oldme.uv_layers];colors=[(a.name,a.data_type,a.domain) for a in oldme.color_attributes]
 with bpy.data.libraries.load(str(O/'Phantom_Canonical.blend'),link=False) as (a,b):b.objects=['Phantom_ContinuousLow','Phantom_SourceHigh']
 low,high=b.objects
 for ob in [low,high]:bpy.context.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False;transform(ob,key)
 cut_body(low,key);low.data.update();high.data.update()
 # Dense source supplies continuous smooth normals in the actual fitted frame.
 active(high)
 for f in high.data.polygons:f.use_smooth=True
 active(low)
 if low.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
 for f in low.data.polygons:f.use_smooth=True
 for e in low.data.edges:e.use_edge_sharp=False
 mod=low.modifiers.new('Dense source corner normals','DATA_TRANSFER');mod.object=high;mod.use_loop_data=True;mod.data_types_loops={'CUSTOM_NORMAL'};mod.loop_mapping='POLYINTERP_NEAREST';bpy.ops.object.modifier_apply(modifier=mod.name)
 # Preserve the atlas; use non-collapsed physical projection on legacy extra channels.
 me=low.data;atlas=np.asarray([tuple(v.uv) for v in me.uv_layers[0].data]);normal=[tuple(n.vector) for n in me.corner_normals]
 for uv in list(me.uv_layers):me.uv_layers.remove(uv)
 while len(uvnames)<2:uvnames.append('SurfaceCoating')
 coat=projected(me,(.12,.05 if key in ['M4','M16','HK416','Super90'] else .025))
 physical=projected(me,(.04,.04));tri=np.asarray([list(f.vertices) for f in me.polygons]);points=np.asarray([tuple(v.co) for v in me.vertices]);q=points[tri];a=atlas.reshape(-1,3,2);ar=(a[:,1,0]-a[:,0,0])*(a[:,2,1]-a[:,0,1])-(a[:,1,1]-a[:,0,1])*(a[:,2,0]-a[:,0,0]);bad=abs(ar)<2e-14;a[bad]=physical[bad]
 for i,name in enumerate(uvnames):
  uv=me.uv_layers.new(name=name);values=a if i==0 or (key=='M16' and i==2) else (coat if i==1 else physical);uv.data.foreach_set('uv',values.astype(np.float32).ravel())
 # Match existing per-corner metal/polymer masks by nearest source surface.
 if colors:
  active(low);names=[(a.name,a.data_type,a.domain) for a in oldme.color_attributes]
  for name,typ,domain in names:me.color_attributes.new(name=name,type=typ,domain=domain)
  mod=low.modifiers.new('Preserve existing surface region masks','DATA_TRANSFER');mod.object=old;mod.use_loop_data=True;mod.data_types_loops={'COLOR_CORNER'};mod.loop_mapping='POLYINTERP_NEAREST'
  bpy.ops.object.datalayout_transfer(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
 me.materials.clear()
 for m in oldslots:me.materials.append(m)
 for f in me.polygons:f.material_index=body_slot
 me.normals_split_custom_set(normal)
 # Keep every current interface face, UV, color and corner normal.
 preserve_normals(oldme);bm=bmesh.new();bm.from_mesh(oldme);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==body_slot],context='FACES');bm.to_mesh(oldme);bm.free();restore_normals(oldme)
 active(low);old.select_set(True);bpy.ops.object.join();bpy.data.objects.remove(high,do_unlink=True)
 ob=low;ob.name=row['path'].rsplit('/',1)[1];me=ob.data;me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
 # Unused static slots are retained so existing runtime overrides keep their indices.
 while len(me.materials)<len(row['slots']):me.materials.append(bpy.data.materials.new(row['slots'][len(me.materials)]['name']))
 fbx=OUT/(key+'.fbx');blend=OUT/(key+'.blend');active(ob)
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(blend));R['assets'][key]={'fbx':str(fbx),'blend':str(blend),'body_slot':body_slot,'triangles':len(me.polygons),'preserved_interface_triangles':before_interface,'repaired_degenerate_uv_faces':int(bad.sum()),'materials':[m.name for m in me.materials],'source_family':'AKM' if key in ['AKM','A762','PKM'] else ('QBZ191' if key=='QBZ191' else 'M4')}
 (O/'production.json').write_text(json.dumps(R,indent=2));print('PHANTOM_AUTHORED',key,R['assets'][key],flush=True)
R['eight_bodies_complete']=True;(O/'production.json').write_text(json.dumps(R,indent=2))
