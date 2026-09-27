import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
d=np.load(O/'factory_surface.npz');p=d['vertices'];tri=p[d['triangles']];tri=tri[d['material_ids']==0]
# Numeric surface profiles for selecting a complete original stamped panel.
a=tri[:,0,1:];b=tri[:,1,1:]-a;c=tri[:,2,1:]-a
den=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=abs(den)>1e-12
for y in [-.015,0,.012,.027,.045]:
 row=[]
 for t in np.arange(-.024,.0321,.002):
  v=np.array([y,t-.21871*y])-a
  u=np.divide(v[:,0]*c[:,1]-v[:,1]*c[:,0],den,out=np.zeros(len(den)),where=valid)
  w=np.divide(b[:,0]*v[:,1]-b[:,1]*v[:,0],den,out=np.zeros(len(den)),where=valid)
  mask=valid&(u>=-1e-6)&(w>=-1e-6)&(u+w<=1.000001)
  xs=tri[:,0,0]+u*(tri[:,1,0]-tri[:,0,0])+w*(tri[:,2,0]-tri[:,0,0])
  row.append(round(float(xs[mask].max()*1000),2) if mask.any() else None)
 print('SVD_PATTERN',y,'t -24..32 step2 mm',row,flush=True)
source=O.parent/'SVDReloadLeftArm20260925/Blends/SVD_base_reload_LeftArm.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;scene.frame_set(220)
rig=next(o for o in scene.objects if o.type=='ARMATURE' and 'WPN_SOCKET_Magazine' in o.data.bones)
xf=(rig.matrix_world@rig.pose.bones['WPN_SOCKET_Magazine'].matrix).inverted()@rig.matrix_world
rows={}
for bone in rig.pose.bones:
 if bone.name=='hand_l' or (bone.name.endswith('_l') and any(n in bone.name for n in ['index_','middle_','ring_','pinky_','thumb_'])):
  pos=xf@bone.head;rows[bone.name]=[round(v,5) for v in pos]+[round(pos.z+.21871*pos.y,5)]
(O/'grasp_source.json').write_text(json.dumps({'source':str(source),'frame':220,'bones_socket_xyz_t':rows},indent=2))
print('SVD_GRASP '+json.dumps(rows),flush=True)
