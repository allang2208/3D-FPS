"""Continuous support for RSH inspect while the left hand keeps its grasp.

The accepted idle arm is transported with the held palm as a single chain.
Unlike 715's free-hand inspection, this support does not release its grip, so
it must not inherit that animation's clavicle spins or choose new elbow poles.
"""
class InspectSupport:
    def __init__(self, reference, rest):
        self.ref={n:m.copy() for n,m in reference.items()}
        self.inverse_hand=self.ref['hand_l'].inverted()
        self.names=[n for n in reference if n.endswith('_l') and
                    n.startswith(('clavicle','upperarm','lowerarm'))]

    def apply(self, pose):
        delta=pose['hand_l']@self.inverse_hand
        for name in self.names:
            pose[name]=delta@self.ref[name]
        # The wrist world transform is already correct. Re-author its local
        # rotation because the support parent has changed.
        return set(self.names)|{'hand_l'}


def rewrite_inspect(rig, data, profile):
    """Replace one clip in a freshly authored profile; retain every other row."""
    from mathutils import Matrix
    from grip_scene import pose, matrix, applied
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    reference=pose(rig,data,profile,'idle',data['clips']['idle']['samples'][0])
    solver=InspectSupport(reference,rest)
    entry=next(e for e in profile['clips'] if e['kind']=='inspect')
    reflect=Matrix.Diagonal((1,-1,1,1))
    to_ue=(rig.matrix_world.inverted()@reflect@Matrix.Diagonal((.01,.01,.01,1))).inverted()
    times=[];tracks={};previous={}
    for sample in data['clips']['inspect']['samples']:
        t=sample['time'];times.append(t);p=pose(rig,data,profile,'inspect',sample)
        changed=solver.apply(p)
        world={n:to_ue@m@reflect for n,m in p.items()}
        original=applied({n:matrix(v) for n,v in sample['local'].items()},entry,t)
        for n in changed:
            parent=data['parents'][n];lp=world[parent].inverted()@world[n]
            nt,nq,ns=lp.decompose();bt,bq,bs=matrix(sample['local'][n]).decompose()
            if n!='clavicle_l':nt=original[n].translation
            q=nq@bq.inverted()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy()
            tracks.setdefault(n,[]).append([*(nt-bt),q.x,q.y,q.z,q.w,*(original[n].to_scale()-bs)])
    existing={tr['bone']:tr for tr in entry['tracks']}
    for n,values in tracks.items():existing[n]=dict(bone=n,times=times,values=[v for row in values for v in row])
    entry['tracks']=list(existing.values())
    return dict(clip='inspect',samples=len(times),bones=list(tracks),support_mode='held_inspect_chain')
