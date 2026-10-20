"""Own-weapon idle grasp + existing M870/SVD whole-arm support, no new motion."""
from diagnose_grip import O,R6,R5,s,measure
from pathlib import Path
import sys,json,importlib.util,numpy as np
from scipy.optimize import least_squares
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R
sys.path.insert(0,str(R5))
spec=importlib.util.spec_from_file_location('existing_elbow_support',R5/'author_m870.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
base_local=np.load(R6/'desired-local-120.npz');original={f:np.array([s.comp(s.matrices(p)) for p in base_local[f]]) for f in base_local.files}
capture=json.loads((R6/'native-saved-glove.json').read_text());idle={}
for f in capture['families']:
    order=[f['names'].index(n) for n in s.names];idle[f['family']]=s.matrices(np.array(f['frames'][0]['bones'])[order])
root,h,u,l=[s.ids[n] for n in ['WPN_root','hand_r','upperarm_r','lowerarm_r']]
right=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
digits=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
source=original['base'].copy();grip=s.relative(idle['base'][root],idle['base'][h])
for i,p in enumerate(source):
    old=original['base'][i];target=p[root]@grip;shift=target[:3,3]-old[h,:3,3]
    # Move the support as a whole, then solve at exact native lengths. The
    # accepted finger LOCAL transforms follow the re-seated palm unchanged.
    p[right,:3,3]+=shift;p[h]=target
    for j in digits:p[j]=p[s.parents[j]]@s.relative(old[s.parents[j]],old[j])
support.source=source
times=support.times
# The reseated grip is now the idle contact throughout the action. Keep wrist
# support through recovery and fade to that same idle endpoint, not the R4
# bent-wrist support that R5 resumed at frame 84.
support.active=s.ease(5/120,.14,times)*(1-s.ease(.78,.9,times))
active=support.active

def main():
    knots=list(range(0,len(times),2));controls=[];rolls=[];previous=np.zeros(4);reference=0.
    lower=np.array([-14.,-14.,-18.,-.85]);upper=-lower
    for i in knots:
        if active[i]<1e-8:
            controls.append(np.zeros(4));reference=support.pose(i,controls[-1],reference)[-1]
            rolls.append(reference);previous=controls[-1].copy();continue
        a_base=source[i,u,:3,3];e_base=source[i,l,:3,3];guess=np.clip(previous,lower+1e-6,upper-1e-6)
        def residual(x):
            p,a,e,hand,wrist_axis,roll=support.pose(i,x,reference)
            cut=support.points(p,support.CUT,i);arm=support.points(p,support.ARM,i)
            opening=np.maximum(0.,cut@support.corner_normal+support.corner_margin)*s.ease(0,5,cut[:,0])
            eye=np.maximum(0.,14.-np.linalg.norm(arm,axis=1))
            return np.r_[opening/.055,eye/.35,(s.unit(hand-e)-wrist_axis)/.04,
                (a-a_base)/np.array([7.,7.,9.]),(e-e_base)/8.,x[3]/.55,
                (x-guess)/np.array([3.,3.,3.,.35]),max(0.,abs(roll)-np.radians(110))/np.radians(12.),max(0.,e[2]-hand[2]+1.)/5.]
        fit=least_squares(residual,guess,bounds=(lower,upper),max_nfev=65,ftol=2e-5,xtol=2e-5,gtol=2e-5)
        controls.append(fit.x);previous=fit.x;reference=support.pose(i,fit.x,reference)[-1];rolls.append(reference)
    dense=PchipInterpolator(times[knots],controls,axis=0)(times);roll_dense=PchipInterpolator(times[knots],rolls)(times)
    result=np.array([support.pose(i,x,roll_dense[i])[0] for i,x in enumerate(dense)])
    # Both endpoints retain the exact currently installed idle.
    result[0]=original['base'][0];result[-1]=original['base'][-1]
    poses={};local={};report={}
    fixed=[j for j in range(len(s.names)) if j not in right]
    for family,old in original.items():
        assert np.max(abs(old[:,right]-original['base'][:,right]))<.001
        q=old.copy();q[:,right]=result[:,right];poses[family]=q;keys=[]
        for p in q:
            row=[]
            for j,par in enumerate(s.parents):
                m=s.relative(p[par],p[j]) if par>=0 else p[j]
                row.append(np.r_[m[:3,3],R.from_matrix(s.rigid(m)[:3,:3]).as_quat(),np.linalg.norm(m[:3,:3],axis=0)])
            keys.append(row)
        local[family]=np.array(keys);measures=[{'frame':i,**measure(p,idle[family])} for i,p in enumerate(q)]
        report[family]={'left_weapon_matrix_difference':float(abs(q[:,fixed]-old[:,fixed]).max()),
            'max_native_offset_error_cm':max(max(s.offsets(p).values()) for p in q),'frames':measures}
    np.savez_compressed(O/'poses.npz',**poses);np.savez_compressed(O/'desired-local-120.npz',**local)
    (O/'authoring.json').write_text(json.dumps({'method':'Own SVCH idle palm registration; unchanged grouped finger locals; existing M870 R3 whole-arm support',
        'controls':dense.tolist(),'forearm_roll':roll_dense.tolist(),'families':report},indent=2))
    print('R7_GRIP_AUTHORED',json.dumps({f:{'wrist_max':max(r['wrist_axis_bend_degrees'] for r in x['frames']),
        'grip_offset_cm':max(r['grip_offset_cm'] for r in x['frames']),'grip_rotation':max(r['grip_rotation_degrees'] for r in x['frames']),
        'native_offset_cm':x['max_native_offset_error_cm']} for f,x in report.items()}),flush=True)

if __name__=='__main__':main()
