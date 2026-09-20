"""Recover the common design frame from the actual three deployed drum sources."""
import bpy,bmesh,json,itertools,math
import numpy as np
from mathutils import Matrix,Vector,kdtree
from pathlib import Path
O=Path(__file__).resolve().parents[1];S=O.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
meta=json.loads((O/'Reference/current_assets.json').read_text())
d=json.loads((S/'M4Drum20260909/build.json').read_text())
native=Matrix(d['source_to_component'])@Matrix.Translation(Vector(d['center']))
seeds={'M4':native.copy()}
bpy.ops.wm.open_mainfile(filepath=str(S/'AKMSoviet20260911/AKM_Soviet_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima'];action=bpy.data.actions['AKM_Native_idle']
rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
root=rig.pose.bones['WPN_root'].matrix.copy();mag=rig.pose.bones['WPN_SOCKET_Magazine'].matrix.copy()
seeds['AKM']=mag.inverted()@root@Matrix.Translation((.0008,-.002,-.022))@Matrix(json.loads((S/'AKMAttachments20260911/m4_root_inverse.json').read_text()))@native
qbz_inputs=json.loads((S/'QBZ191Attachments20260913/geometry_inputs.json').read_text())
qbz_models=json.loads((S/'QBZ191Attachments20260913/models.json').read_text())
seeds['QBZ191']=Matrix(qbz_inputs['qbz']['mag0']).inverted()@Matrix(qbz_models['parts']['drum']['asset_to_qbz_root'])@native
bpy.ops.wm.read_factory_settings(use_empty=True)
def load(path):
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(path))
 objects=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 if len(objects)>1:bpy.ops.object.join()
 o=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 return o
base=load(S/'M4Drum20260909/SM_M4_LargeDrum.fbx')
base.data.transform(native.inverted())
canon=np.array([tuple(v.co) for v in base.data.vertices],dtype=float)
# The lower original shell is identical across the fitted variants. Use that
# identity to recover each source frame; the neck itself is copied from that gun.
source=canon[canon[:,2]<-.024]
source=source[::max(1,len(source)//1600)]
report={}
for gun,info in meta.items():
 ob=load(info['import_source']);ob.name=gun+'_CurrentSource'
 pts=np.array([tuple(v.co) for v in ob.data.vertices],dtype=float)
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(Vector(p),i)
 kd.balance()
 center=(pts.min(0)+pts.max(0))/2
 reference_center=(canon.min(0)+canon.max(0))/2
 best=None
 for perm in itertools.permutations(range(3)):
  for signs in itertools.product([-1,1],repeat=3):
   R=np.zeros((3,3))
   for row,col in enumerate(perm):R[row,col]=signs[row]
   if np.linalg.det(R)<0:continue
   R=R@np.array(seeds[gun].to_3x3().normalized());t=center-R@reference_center
   for _ in range(70):
    transformed=source@R.T+t
    matches=[kd.find(Vector(v)) for v in transformed]
    dst=np.array([pts[q[1]] for q in matches]);dist=np.array([q[2] for q in matches])
    keep=dist<=np.quantile(dist,.90)
    a=source[keep];b=dst[keep];ac=a.mean(0);bc=b.mean(0)
    U,_,Vt=np.linalg.svd((a-ac).T@(b-bc))
    Rn=Vt.T@U.T
    if np.linalg.det(Rn)<0:Vt[-1,:]*=-1;Rn=Vt.T@U.T
    tn=bc-Rn@ac
    if np.max(np.abs(R-Rn))<1e-9 and np.max(np.abs(t-tn))<1e-9:break
    R,t=Rn,tn
   distances=np.array([kd.find(Vector(v))[2] for v in source@R.T+t])
   score=float(np.quantile(distances,.90))
   if best is None or score<best[0]:best=(score,R.copy(),t.copy())
 score,R,t=best
 print('FRAME_FIT',gun,score,R.tolist(),t.tolist(),flush=True)
 if score>.00015:raise RuntimeError('Could not recover source interface frame '+gun+' '+str(score))
 A=Matrix.Identity(4)
 for i in range(3):
  for j in range(3):A[i][j]=R[i,j]
  A[i][3]=t[i]
 ob.data.transform(A.inverted())
 ob['canonical_to_source']=json.dumps([list(row) for row in A])
 ob.hide_set(True);ob.hide_render=True
 report[gun]={'canonical_to_source':[list(row) for row in A],
 'retained_neck_cut_z_m':-.0215,'original_import_source':info['import_source'],
 'source_frame_recovery_p90_m':score,'runtime_asset':info['asset']}
 print('RECOVERED_FRAME',gun,score,flush=True)
bpy.data.objects.remove(base,do_unlink=True)
(O/'Reference/author_frames.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Source/OriginalDrumInterfaces.blend'))
print('DRUM_INTERFACE_SOURCES_READY',flush=True)
