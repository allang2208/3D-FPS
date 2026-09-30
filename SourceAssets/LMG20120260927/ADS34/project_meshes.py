"""Reproduce current 201 ADS skinning and garment leader poses offline."""
import bpy,json,numpy as np
from mathutils import Matrix,Vector,Quaternion
from pathlib import Path
O=Path(__file__).parent;data=json.loads((O/'sources.json').read_text())['meshes'];body=data['201'];aim=body['poses']['aim']
def mat(t):return np.array(Matrix.Translation(Vector(t['p']))@Quaternion((t['q'][3],*t['q'][:3])).to_matrix().to_4x4()@Matrix.Diagonal(Vector((*t['s'],1))))
rear=Vector(aim['WPN_RearSight']['p']);front=Vector(aim['WPN_FrontSight']['p']);axis=(front-rear).normalized();base=Quaternion((0,0,1),np.pi/2);rot=(base@axis).rotation_difference(Vector((1,0,0)))@base;R=np.array(rot.to_matrix());loc=np.array((20.,0.,0.))-R@np.array(rear)
report={'rotation':R.tolist(),'location':loc.tolist(),'meshes':{}}
for key,d in data.items():
 if not (O/(key+'.fbx')).exists():continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/(key+'.fbx')))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
 names=[b.name for b in rig.data.bones if b.name in d['rest']]
 X=np.array([list(rig.matrix_world@rig.data.bones[n].head_local)+[1] for n in names]);Y=np.array([d['rest'][n]['p'] for n in names]);conv=np.linalg.lstsq(X,Y,rcond=None)[0].T
 skin={n:mat(aim[n])@np.linalg.inv(mat(d['rest'][n])) for n in names if n in aim}
 points=[];restpoints=[];faces=[];mids=[];mnames=[];offset=0;missing={};bonemass={}
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  ps=np.array([list(ob.matrix_world@v.co)+[1] for v in ob.data.vertices])@conv.T;posed=np.zeros_like(ps);weight=np.zeros(len(ps));groups={g.index:g.name for g in ob.vertex_groups};perbone={}
  for v in ob.data.vertices:
   for g in v.groups:
    if g.weight<=0:continue
    n=groups[g.group];perbone.setdefault(n,[]).append((v.index,g.weight))
  for n,rows in perbone.items():
   ids=np.array([x[0] for x in rows]);ww=np.array([x[1] for x in rows]);bonemass[n]=bonemass.get(n,0)+float(ww.sum())
   if n not in skin:
    missing[n]=missing.get(n,0)+len(ids);m=np.eye(4)
   else:m=skin[n]
   posed[ids]+=(ps[ids]@m[:3,:3].T+m[:3,3])*ww[:,None];weight[ids]+=ww
  valid=weight>1e-6;posed[valid]/=weight[valid,None];posed[~valid]=ps[~valid];points.append(posed@R.T+loc);restpoints.append(ps)
  ob.data.calc_loop_triangles();mo=len(mnames);mnames.extend(m.name if m else 'None' for m in ob.data.materials)
  for t in ob.data.loop_triangles:faces.append([i+offset for i in t.vertices]);mids.append(mo+t.material_index)
  offset+=len(ps)
 pp=np.concatenate(points);rp=np.concatenate(restpoints);ff=np.array(faces);mi=np.array(mids)
 meshreport={'fit_error_cm':float(np.max(np.linalg.norm(X@conv.T-Y,axis=1))),'missing_weighted_bones':missing,'materials':[],'bone_weight_mass':bonemass}
 for i,n in enumerate(mnames):
  ids=np.unique(ff[mi==i]);v=pp[ids]
  if not len(v):continue
  right=(v[:,0]>.1)&(v[:,1]>.6*v[:,0])&(v[:,1]<v[:,0])&(np.abs(v[:,2])<.6*v[:,0])
  meshreport['materials'].append({'name':n,'camera_bounds_cm':np.stack([v.min(0),v.max(0)]).tolist(),'right_edge_vertices':int(right.sum())})
 report['meshes'][key]=meshreport
 np.savez_compressed(O/(key+'_projection.npz'),points=pp,rest=rp,faces=ff,material_ids=mi,material_names=np.array(mnames))
 print('ADS34_PROJECTED',key,meshreport['missing_weighted_bones'],flush=True)
(O/'projection.json').write_text(json.dumps(report,indent=2))
