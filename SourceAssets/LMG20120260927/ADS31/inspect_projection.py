"""Offline component projection for the specifically reported iron-sight ADS bug."""
import bpy,json,numpy as np
from mathutils import Matrix,Vector,Quaternion
from pathlib import Path
O=Path(__file__).parent;data=json.loads((O/'aim.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'SK_LMG201_ADS31_Before.fbx'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
def matrix(t):return Matrix.Translation(Vector(t['p']))@Quaternion((t['q'][3],*t['q'][:3])).to_matrix().to_4x4()@Matrix.Diagonal(Vector((*t['s'],1)))
names=[b.name for b in rig.data.bones if b.name in data['rest']]
X=np.array([list(rig.matrix_world@rig.data.bones[n].head_local)+[1] for n in names]);Y=np.array([data['rest'][n]['p'] for n in names])
conv=np.linalg.lstsq(X,Y,rcond=None)[0].T
skin={n:np.array(matrix(data['aim'][n])@matrix(data['rest'][n]).inverted()) for n in names}
rear=Vector(data['aim']['WPN_RearSight']['p']);front=Vector(data['aim']['WPN_FrontSight']['p'])
axis=(front-rear).normalized();base=Quaternion((0,0,1),np.pi/2)
rot=(base@axis).rotation_difference(Vector((1,0,0)))@base
R=np.array(rot.to_matrix());location=np.array((20.,0.,0.))-R@np.array(rear)
report={'affine_fit_error_cm':float(np.max(np.linalg.norm((X@conv.T)-Y,axis=1))),
 'bone_alignment':conv.tolist(),'eye_offset':location.tolist(),'view_rotation':list(rot),'materials':[]}
arrays=[];faces=[];matindices=[];offset=0;allmats=[];allnames=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 ps=np.array([list(ob.matrix_world@v.co)+[1] for v in ob.data.vertices])@conv.T
 posed=np.zeros_like(ps);weight=np.zeros(len(ps));groups={g.index:g.name for g in ob.vertex_groups}
 for gi,name in groups.items():
  if name not in skin:continue
  ids=[];ww=[]
  for v in ob.data.vertices:
   for g in v.groups:
    if g.group==gi and g.weight>0:ids.append(v.index);ww.append(g.weight)
  if ids:
   ww=np.array(ww);ids=np.array(ids);m=skin[name]
   posed[ids]+=(ps[ids]@m[:3,:3].T+m[:3,3])*ww[:,None];weight[ids]+=ww
 good=weight>1e-6;posed[good]/=weight[good,None];posed[~good]=ps[~good]
 cam=posed@R.T+location;arrays.append(cam)
 ob.data.calc_loop_triangles();moffset=len(allmats);allmats.extend(m.name if m else 'None' for m in ob.data.materials)
 for t in ob.data.loop_triangles:faces.append([i+offset for i in t.vertices]);matindices.append(moffset+t.material_index)
 offset+=len(ps)
points=np.concatenate(arrays);faces=np.array(faces);matindices=np.array(matindices)
for i,name in enumerate(allmats):
 ids=np.unique(faces[matindices==i]);p=points[ids]
 if len(p)==0:continue
 visible=(p[:,0]>.1)&(p[:,1]>-.9*p[:,0])&(p[:,1]<.9*p[:,0])&(np.abs(p[:,2])<.51*p[:,0])
 close=visible&(p[:,0]<20)&(p[:,1]>2)
 report['materials'].append({'name':name,'bounds_camera_cm':[[float(p[:,k].min()),float(p[:,k].max())] for k in range(3)],'right_near_vertices':int(close.sum()),'visible_vertices':int(visible.sum())})
np.savez_compressed(O/'projected.npz',points=points,faces=faces,material_ids=matindices,material_names=np.array(allmats))
(O/'projection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
