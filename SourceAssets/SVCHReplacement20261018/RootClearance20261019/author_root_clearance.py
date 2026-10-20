"""Author SVCH-specific shoulder clearance; do not reshape or rescale V9."""
from shoulder_support import *
import copy
from scipy import sparse
from scipy.optimize import lsq_linear

TARGET_MARGIN=.08
ASPECT=21/9
MAX_BACK=8.
changed=[j for j,n in enumerate(names) if n in ('clavicle_l','hand_l') or (n.endswith('_l') and n.startswith(('upperarm','lowerarm')))]
out=copy.deepcopy(profile)
report={'source_profile_sha256':json.loads((O/'Inputs/manifest.json').read_text())['profile']['sha256'],
 'native_v9_sha256':arms['sha256'],'method':'Rigid shoulder translation with fixed-length two-bone support, closest existing elbow, unchanged palm world transform',
 'camera_vertical_fov':75,'authoring_aspect':ASPECT,'root_margin':TARGET_MARGIN,
 'V9_mesh_weights_rest_morphs_written':False,'shared_animations_written':False,'runtime_tested':False,'clips':{}}

for role in ('reload','reload_empty'):
    c=motion['clips'][role];src=next(x for x in profile['clips'] if x['base']==c['path']);dst=next(x for x in out['clips'] if x['base']==c['path'])
    count=len(c['times']);poses=[pose(role,i) for i in range(count)];cams=[cam_at(role,i) for i in range(count)]
    need=np.zeros(count);limit=np.zeros(count);baseline_visible=[];retained_edge_frames=[]
    for i,(p,cam) in enumerate(zip(poses,cams)):
        pts=root_points(p,cam);margin=float(screen_margin(pts,ASPECT).min());baseline_visible.append(int((screen_margin(pts,ASPECT)<0).sum()))
        A,E,H=transform(cam,p[[ui,li,hi],:3,3]);l1=np.linalg.norm(E-A);l2=np.linalg.norm(H-E);D=H-A
        # Existing near-straight recovery poses are preserved; the correction
        # itself may not straighten the support beyond 96.5% of native reach.
        radius=(l1+l2)*.965;cap=-D[0]+np.sqrt(max(0,radius*radius-D[1]*D[1]-D[2]*D[2]))
        cap=float(np.clip(cap,0,MAX_BACK))
        # The same bound applies during smoothing, including frames that did
        # not individually require a shift. Keep wrist/forearm changes small.
        lo,hi_cap=0.,cap
        for _ in range(14):
            mid=(lo+hi_cap)*.5;q,s=shift_shoulder(p,cam,[-mid,0,0])
            if q is not None and s['forearm_direction_change_deg']<=14. and abs(s['additional_axial_deg'])<=12.:lo=mid
            else:hi_cap=mid
        cap=lo;limit[i]=cap
        if margin>=TARGET_MARGIN:continue
        best=None
        for back in np.arange(.125,cap+.001,.125):
            q,s=shift_shoulder(p,cam,[-back,0,0])
            if q is None:continue
            if s['forearm_direction_change_deg']>14. or abs(s['additional_axial_deg'])>12.:break
            m=float(screen_margin(root_points(q,cam),ASPECT).min())
            if m>=TARGET_MARGIN:
                best=float(back);break
        if best is None:
            # Already outside the wide frame: retain its accepted recovery
            # instead of straightening the elbow merely to add extra padding.
            if margin>=0:
                retained_edge_frames.append(i);continue
            raise RuntimeError(f'No natural fixed-length support at {role} frame {i}; do not force the wrist')
        need[i]=best
    # Solve one continuous displacement curve, rather than choosing unrelated
    # shoulder offsets at each frame. Small amplitude cost keeps it local.
    D1=sparse.diags([-np.ones(count-1),np.ones(count-1)],[0,1],shape=(count-1,count))
    D2=sparse.diags([np.ones(count-2),-2*np.ones(count-2),np.ones(count-2)],[0,1,2],shape=(count-2,count))
    A=sparse.vstack([D2*40,D1*2,sparse.eye(count)*.12]).tocsr()
    upper_bound=np.maximum(limit,need+1e-8);need[0]=need[-1]=0;upper_bound[0]=upper_bound[-1]=0
    free=np.flatnonzero(upper_bound>1e-6)
    sol=lsq_linear(A[:,free].toarray(),np.zeros(A.shape[0]),bounds=(need[free],upper_bound[free]),method='bvls',tol=1e-8,max_iter=500)
    if not sol.success:raise RuntimeError('Shoulder curve solve did not converge: '+sol.message)
    curve=np.zeros(count);curve[free]=sol.x;curve[curve<.01]=0;curve[0]=curve[-1]=0
    values={j:[] for j in changed};stats=[];max_bone=0.;max_hand=0.;max_forearm=0.;max_axial=0.
    for i,(t,p,cam,back) in enumerate(zip(c['times'],poses,cams,curve)):
        if back>0:
            q,s=shift_shoulder(p,cam,[-back,0,0])
            if q is None:raise RuntimeError('Unreachable support curve')
            if s['forearm_direction_change_deg']>16. or abs(s['additional_axial_deg'])>14.:raise RuntimeError(f'Excessive wrist compensation: {role} {i} {s}')
        else:q=p;s={'reach':float(np.linalg.norm(p[hi,:3,3]-p[ui,:3,3])/(np.linalg.norm(p[li,:3,3]-p[ui,:3,3])+np.linalg.norm(p[hi,:3,3]-p[li,:3,3]))),'forearm_direction_change_deg':0.,'additional_axial_deg':0.,'elbow_move_cm':0.}
        max_hand=max(max_hand,float(abs(q[hi]-p[hi]).max()))
        for a,b in ((ci,ui),(ui,li),(li,hi)):
            max_bone=max(max_bone,abs(float(np.linalg.norm(q[b,:3,3]-q[a,:3,3])-np.linalg.norm(p[b,:3,3]-p[a,:3,3]))))
        max_forearm=max(max_forearm,s['forearm_direction_change_deg']);max_axial=max(max_axial,abs(s['additional_axial_deg']))
        raw=np.asarray(c['frames'][i])
        for j in changed:
            oldtrack=next((tr for tr in src['tracks'] if tr['bone']==names[j]),None)
            oldvalue=sample(t,oldtrack) if oldtrack else np.array([0,0,0,0,0,0,1,0,0,0],float)
            if back==0:v=oldvalue.copy()
            else:
                local=relative(q[parents[j]],q[j]);scale=np.linalg.norm(local[:3,:3],axis=0)
                v=np.r_[local[:3,3]-raw[j,:3],(R.from_matrix(local[:3,:3]/scale)*R.from_quat(raw[j,3:7]).inv()).as_quat(),oldvalue[7:10]]
            if values[j] and values[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values[j].append(v)
        stats.append({'frame':i,'shoulder_back_cm':float(back),**s})
    dst['tracks']=[tr for tr in dst['tracks'] if ids[tr['bone']] not in changed]+[{'bone':names[j],'times':c['times'],'values':np.round(values[j],10).ravel().tolist()} for j in changed]
    report['clips'][role]={'max_shoulder_back_cm':float(curve.max()),'max_shoulder_step_cm':float(abs(np.diff(curve)).max()),
       'max_forearm_direction_change_deg':max_forearm,'max_additional_forearm_axial_deg':max_axial,
       'construction_palm_matrix_delta':max_hand,'construction_bone_length_delta_cm':max_bone,
       'baseline_wide_root_visible_frames':sum(v>0 for v in baseline_visible),'modified_frame_range':[int(np.flatnonzero(curve)[0]),int(np.flatnonzero(curve)[-1])],
       'already_clear_recovery_frames_retained_for_joint_shape':retained_edge_frames,
       'palm_fingers_right_hand_and_mechanical_tracks_preserved':True}
    (O/(role+'_support_curve.json')).write_text(json.dumps(stats,indent=2))
    print('SVCH_ROOT_CLEARANCE_AUTHORED',role,json.dumps(report['clips'][role]),flush=True)
(O/'profile_root_clearance.json').write_text(json.dumps(out,separators=(',',':')))
(O/'authoring_recipe.json').write_text(json.dumps(report,indent=2))
