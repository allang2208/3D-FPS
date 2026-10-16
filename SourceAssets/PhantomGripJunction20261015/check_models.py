import bpy,bmesh,json,numpy as np,sys
from pathlib import Path
from mathutils import Matrix,Vector,kdtree
O=Path(__file__).parent;W=O/'Working';D=json.loads((O/'capture.json').read_text());R={};C={'assets':{},'complete':False,'unchanged':['LMG201'],'gameplay_tested':False}
HK=np.array(json.loads((O.parent/'HK416Reworked20260930/authoring.json').read_text())['root_matrix']);HI=np.linalg.inv(HK)
for key in ['M4','M16','AKM','QBZ191','PKM','HK416','A762','Super90']:
 row=json.loads((O/(key+'_authoring.json')).read_text());C['assets'][key]=row;bpy.ops.wm.open_mainfile(filepath=row['blend']);bpy.context.preferences.filepaths.save_version=0;ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;triangulated=any(len(f.vertices)!=3 for f in me.polygons)
 if triangulated:
  a=me.attributes.new('FinalizeNormals','FLOAT_VECTOR','CORNER');a.data.foreach_set('vector',np.asarray([tuple(n.vector) for n in me.corner_normals],dtype=np.float32).ravel());bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.to_mesh(me);bm.free();me.normals_split_custom_set([tuple(n.vector) for n in me.attributes['FinalizeNormals'].data]);me.attributes.remove(me.attributes['FinalizeNormals'])
 p=np.array([tuple(ob.matrix_world@v.co) for v in me.vertices]);t=np.array([list(f.vertices) for f in me.polygons]);m=np.array([f.material_index for f in me.polygons]);ns=np.array([tuple(n.vector) for n in me.corner_normals]);uv=np.array([tuple(v.uv) for v in me.uv_layers[0].data]).reshape(-1,3,2)
 q=p[t];cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);geo=np.linalg.norm(cross,axis=1);ar=abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0]));bad=(geo>2e-12)&(ar<2e-14);badn=np.linalg.norm(ns,axis=1)<.9
 old=np.load(W/(key+'.npz'));op=old['grip_positions'];ot=old['grip_triangles'];om=old['grip_mids'];local=op@HI[:3,:3].T+HI[:3,3] if key=='HK416' else op
 keep=om==row['body_slot']
 if not row.get('whole_body_unchanged'):keep&=local[ot][:,:,2].max(1)<row['cut']-1e-5
 # Position keys ignore winding and triangulation order, but preserve every original triangle.
 def keys(points,triangles,mask):
  return {tuple(sorted(tuple(np.round(points[i],7)) for i in f)) for f in triangles[mask]}
 before=keys(op,ot,keep);after=keys(p,t,m==row['body_slot']);missing=before-after
 r={'triangles':len(t),'preserved_lower_body_triangles':len(before),'missing_lower_body_triangles':len(missing),'invalid_normals':int(badn.sum()),'collapsed_uv0_nondegenerate':int(bad.sum()),'boundaries_use_shared_vertices':row.get('shared_boundary_vertices',False),'untouched_host_asset':D['hosts'][key]['path']}
 if missing:
  current=q[m==row['body_slot']];centers=current.mean(1);kd=kdtree.KDTree(len(current))
  for i,v in enumerate(centers):kd.insert(Vector(v),i)
  kd.balance();remaining=0;maxdelta=0
  for tri in op[ot[keep]]:
   _,i,_=kd.find(Vector(tri.mean(0)));error=np.linalg.norm(tri[:,None,:]-current[i][None,:,:],axis=2).min(1).max();maxdelta=max(maxdelta,float(error));remaining+=error>2e-7
  r['missing_lower_body_triangles']=int(remaining);r['max_lower_position_delta_mm']=maxdelta*1000
  if remaining:raise RuntimeError('Lower gripping geometry changed '+key+' '+str(remaining))
 if badn.any():raise RuntimeError('Invalid normals '+key)
 # New cut/loft microfaces receive a metric UV only if they cannot form a tangent.
 if bad.any():
  uvdata=me.uv_layers[0].data
  for fi in np.flatnonzero(bad):
   axes=[i for i in range(3) if i!=np.argmax(abs(cross[fi]))]
   for li,v in zip(me.polygons[int(fi)].loop_indices,q[fi]):uvdata[li].uv=(v[axes[0]]/.04,v[axes[1]]/.04)
  r['uv0_repaired']=int(bad.sum());r['collapsed_uv0_nondegenerate']=0
 if bad.any() or triangulated:
  bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.ops.export_scene.fbx(filepath=row['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False);bpy.ops.wm.save_as_mainfile(filepath=row['blend'])
 row['triangles']=len(me.polygons)
 R[key]=r;(O/'geometry_review.json').write_text(json.dumps(R,indent=2));print('JUNCTION_GEOMETRY_REVIEW',key,r,flush=True)
C['complete']=True;(O/'production.json').write_text(json.dumps(C,indent=2));print('JUNCTION_MODELS_READY',flush=True)
