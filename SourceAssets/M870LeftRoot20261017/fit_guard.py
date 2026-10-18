"""Fit a bounded shoulder guard; preserve the entire arm shape about its wrist."""
from analyze import *

def controls(pc):
    # A box includes empty corners and would unnecessarily lower the safe idle
    # by 7-9 degrees. Use the two real authored rims, not their empty volume.
    return np.concatenate([skin(pc,G[key]) for key in ('shirt','skin')])
def correction(pc,tangent=tv):
    points=controls(pc);normal=unit(np.array([tangent,0.,1.]));height=points@normal;maximum=float(height.max())
    d=max(0.,maximum+1.);needed=d*d/(d+.75)
    if needed<1e-8 or points[:,0].max()<0.:return I.copy(),0.
    wrist=pc['hand_l'][:3,3];v=points-wrist;axis=unit(np.cross(normal,points.mean(0)-wrist))
    along=v@axis;constant=(normal@wrist)+(normal@axis)*along
    a=v@normal-(normal@axis)*along;b=np.cross(axis,v)@normal
    target=maximum-needed
    low=0.;high=np.deg2rad(35.)
    for _ in range(12):
        middle=(low+high)*.5
        if np.max(constant+a*np.cos(middle)+b*np.sin(middle))>target:low=middle
        else:high=middle
    q=R.from_rotvec(axis*high).as_matrix();delta=I.copy();delta[:3,:3]=q;delta[:3,3]=wrist-q@wrist
    return delta,high

if __name__=='__main__':
    report={'control_count':sum(len(g['ids']) for g in G.values()),'rows':[],'offline_only':True}
    for family in ['base','vertical','canted','prism','angled']:
        c=camera(family)
        for role,clip in D['clips'].items():
            angles=[];before=after=0;max_after=-1.e9;before_joints=[];after_joints=[]
            for time,raw in zip(clip['times'],decode(role,family)):
                pc={n:c@m for n,m in existing_clearance(support(raw),c).items()};delta,angle=correction(pc);angles.append(float(np.rad2deg(angle)))
                before_joints.append([pc[n][:3,3] for n in ('upperarm_l','lowerarm_l')])
                after_joints.append([(delta@pc[n])[:3,3] for n in ('upperarm_l','lowerarm_l')])
                for key,g in G.items():
                    old=skin(pc,g);new=(np.c_[old,np.ones(len(old))]@delta.T)[:,:3]
                    before+=int(visible(old).any());after+=int(visible(new).any());max_after=max(max_after,float((new@unit(np.array([tv,0,1]))).max()))
            report['rows'].append({'family':family,'role':role,'before_visible_surface_frames':before,'after_visible_surface_frames':after,
                                  'max_angle_deg':max(angles),'start_angle_deg':angles[0],'end_angle_deg':angles[-1],
                                  'max_step_deg':max(abs(np.diff(angles)),default=0.),'max_after_plane_cm':max_after})
            for label,values in [('before',before_joints),('after',after_joints)]:
                report['rows'][-1][label+'_max_joint_step_cm']=float(np.linalg.norm(np.diff(values,axis=0),axis=-1).max()) if len(values)>1 else 0.
        print('M870_ROOT_GUARD_FIT',family,flush=True)
    (O/'guard_fit.json').write_text(json.dumps(report,indent=2))
    print('FIT_SUMMARY',{'failures':[r for r in report['rows'] if r['after_visible_surface_frames']],
                         'max_angle_deg':max(r['max_angle_deg'] for r in report['rows']),
                         'idle':[r for r in report['rows'] if r['role']=='idle']},flush=True)
