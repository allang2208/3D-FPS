import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,sys
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Wrist33'))
from pose import matrix
native=r/('native_final' if (r/'native_final/receipt.json').exists() else 'native')
if (r/'native_delivered/receipt.json').exists():native=r/'native_delivered'
geometry_root=r/('geometry_final' if (r/'geometry_final/receipt.json').exists() else 'geometry')
receipt=json.loads((native/'receipt.json').read_text());result={};selections=[]
names=json.loads((geometry_root/'box_normal_base/geometry.json').read_text())['bones'];ix={n:i for i,n in enumerate(names)}
for row in receipt['cases']:
    if not row['case'].endswith('_60'):continue
    label=row['case'];family='tactical_vertical' if label.startswith('vertical_tactical_') else label.split('_')[0];reference=geometry_root/('box_normal_'+family)
    if family=='prism' and (r/'geometry_prism_final/receipt.json').exists():reference=r/'geometry_prism_final/box_normal_prism'
    if not reference.exists():raise RuntimeError(label)
    N=row['bone_count'];data=np.fromfile(native/(label+'.f32'),np.float32).reshape(-1,6+N*7+14)
    p=data[:,6:6+N*7].reshape(-1,N,7);frames=matrix(np.concatenate([p,np.ones((*p.shape[:2],3))],axis=-1))
    rig=matrix(np.c_[data[:,-14:-7],np.ones((len(data),3))]);eye=matrix(np.c_[data[:,-7:],np.ones((len(data),3))])
    camera_rig=np.linalg.inv(eye)@rig
    camera_hand=(camera_rig@frames[:,ix['hand_l']])[:,:3,3]
    travel=np.linalg.norm(np.diff(camera_hand,axis=0),axis=1)
    events=np.flatnonzero(np.diff(data[:,1])!=0)
    end=int(np.flatnonzero(data[:,1]==3)[0]);boundary=np.linalg.norm(p[end,[ix['upperarm_l'],ix['lowerarm_l'],ix['hand_l']],:3]-p[end-1,[ix['upperarm_l'],ix['lowerarm_l'],ix['hand_l']],:3],axis=1)
    selected=np.flatnonzero(data[:,1]!=2);armids=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand_l'))]
    reference_data=json.loads((reference/'review.json').read_text());last=reference_data['frames'][-1];stem=reference/Path(last['file']).stem
    geometry=json.loads((reference/'geometry.json').read_text());dominant=np.fromfile(reference/'dominant.bin',np.uint32)
    verts=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)
    faces=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);slots=np.fromfile(stem.with_suffix('.materials'),np.uint32)
    skin_ids=np.unique(faces[np.isin(slots,[i for i,n in enumerate(geometry['slots']) if n.startswith('Skin_')])]);skin_ids=skin_ids[np.isin(dominant[skin_ids],armids)]
    refdata=np.fromfile(reference/'poses.f32',np.float32).reshape(-1,4+N*7)[:,4:].reshape(-1,N,7)[-1]
    max_pose_error=float(abs(p[selected][:,armids]-refdata[armids]).max())
    near=0;min_visible=float('inf')
    for k in selected:
        xf=np.linalg.inv(eye[k])@rig[k];v=verts[skin_ids]@xf[:3,:3].T+xf[:3,3]
        inside=(v[:,0]>0)&(abs(v[:,1])<v[:,0]*np.tan(np.radians(107.5/2)))&(abs(v[:,2])<v[:,0]*np.tan(np.radians(107.5/2))*9/16)
        if inside.any():min_visible=min(min_visible,float(v[inside,0].min()));near+=int(((v[:,0]<1.)&inside).sum())
    result[label]=dict(frames=len(data),finite=bool(np.isfinite(data).all()),held_arm_pose_vs_saved_max_error=max_pose_error,
                      max_return_step_cm=float(boundary.max()),owner_camera_near_plane_vertices=near,
                      camera_relative_state_edge_steps_cm=travel[events].tolist(),
                      camera_relative_max_aim_idle_step_cm=float(travel[(data[:-1,1]!=2)&(data[1:,1]!=2)].max()),
                      minimum_visible_skin_forward_cm=min_visible)
    if '_normal_' in label and 'tactical' not in label:
        for phase,name in ((0,'idle'),(1,'ads')):
            k=int(np.flatnonzero(data[:,1]==phase)[-1]);selections.append(dict(family=family,stage=name,reference=str(reference),stem=stem.name,rig=rig[k].tolist(),eye=eye[k].tolist()))
(r/'owner_pose_review.json').write_text(json.dumps(result,indent=2));(r/'owner_view_selections.json').write_text(json.dumps(selections,indent=2))
print('OWNER_POSES',len(result),'cases',sum(v['frames'] for v in result.values()),'frames','near-plane vertices',sum(v['owner_camera_near_plane_vertices'] for v in result.values()),'max held pose difference',max(v['held_arm_pose_vs_saved_max_error'] for v in result.values()))
if any(not v['finite'] or v['held_arm_pose_vs_saved_max_error']>.001 or v['owner_camera_near_plane_vertices'] for v in result.values()):raise RuntimeError('Owner pose requires investigation')
