"""Adapt accepted M870 R3 author_elbow.py to SVD/V9, retaining contact motion.

Same four controls, shared hinge, native 0/50/100 forearm roll and camera /
pronation constraints. SVD adds two upper helpers. Bone lengths stay exact.
"""
from diagnose import O,R4,s,rot,frame,axial,u,l,h,ru,rf,FU,FF,R
import json,numpy as np,sys,importlib.util
from scipy.optimize import least_squares
from scipy.interpolate import PchipInterpolator
sys.path.insert(0,str(R4))
from action_framing import camera_for_frame

def turn(axis,angle):return R.from_rotvec(s.unit(axis)*angle).as_matrix()
def blend(a,b,w):return (R.from_rotvec((R.from_matrix(b)*R.from_matrix(a).inv()).as_rotvec()*w)*R.from_matrix(a)).as_matrix()
data=np.load(R4/'poses.npz');source=data['base'];times=np.array(s.motion['clips']['quick_melee']['times'])
# Native Gunplay readback owns the complete action only from frame 5 through
# frame 84. Outside that interval, preserve R4 exactly: blending altered local
# parents against idle would move the otherwise fixed component-space palm.
active=s.ease(5/120,.14,times)*(1-s.ease(.60,84/120,times))
write=[s.ids[n] for n in ['clavicle_r','upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r']]
la=np.linalg.norm(ru);lb=np.linalg.norm(rf)
minimum=np.sqrt(la*la+lb*lb+2*la*lb*np.cos(np.radians(135)))
maximum=(la+lb)*.95
capture=json.loads((R4/'native-saved-glove.json').read_text())['families'][0]
camera=s.matrices([capture['view_to_camera']])[0]
views=[camera_for_frame(camera,i) for i in range(len(times))]
tv=np.tan(np.radians(37.5));th=tv*2.65
corner_normal=np.array([2.,-1/th,1/tv]);corner_margin=1.0*np.linalg.norm(corner_normal)
T=s.bare.T;edges=np.sort(np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1)
edges,count=np.unique(edges,axis=0,return_counts=True)
vi=s.bare.first[np.unique(edges[count==1])]
bn=np.array([s.names[j] for j in s.bare.weights.argmax(1)])
cut_ids=np.array([j for j in vi if bn[j].startswith(('upperarm','clavicle')) and bn[j].endswith('_r')])
arm_ids=np.array([j for j,n in enumerate(bn) if n.endswith('_r') and n.startswith(('upperarm','lowerarm'))])[::32]
def groups(indices):
    v=np.c_[s.bare.v[indices],np.ones(len(indices))];out=[]
    for j in s.bare.used:
        w=s.bare.weights[indices,j];used=np.flatnonzero(w>0)
        if len(used):out.append((j,used,(v[used]@s.bare.inv[j].T)*w[used,None]))
    return len(indices),out
CUT=groups(cut_ids);ARM=groups(arm_ids)
def points(p,group,i):
    n,bones=group;out=np.zeros((n,3))
    for j,k,v in bones:out[k]+=(v@p[j].T)[:,:3]
    return out@views[i][:3,:3].T+views[i][:3,3]

def pose(i,x,roll_reference):
    original=source[i];p=original.copy();w=active[i]
    H=p[h,:3,3];A=p[u,:3,3]+x[:3]*w
    axis=s.unit(H-A);distance=np.linalg.norm(H-A)
    target=(1-w)*distance+w*np.clip(distance,minimum,maximum)
    A+=axis*(distance-target);distance=target
    pole=original[l,:3,3]-A;pole=s.unit(pole-axis*(pole@axis));pole=turn(axis,x[3]*w)@pole
    along=(la*la-lb*lb+distance*distance)/(2*distance)
    E=A+axis*along+pole*np.sqrt(max(0.,la*la-along*along))
    upper,fore=E-A,H-E;hinge=s.unit(np.cross(upper,fore))
    du=frame(upper,hinge)@FU.T;neutral=frame(fore,hinge)@FF.T
    palm=rot(p[h])@rot(s.ref[h]).T;distal=s.swing(palm@rf,fore)@palm
    roll=np.radians(axial(distal,neutral,fore));roll+=2*np.pi*round((roll_reference-roll)/(2*np.pi))
    old_u=original[l,:3,3]-original[u,:3,3];old_f=original[h,:3,3]-original[l,:3,3]
    upper_swing=s.swing(old_u,upper);fore_swing=s.swing(old_f,fore)
    p[u,:3,3]=A;p[u,:3,:3]=blend(upper_swing@rot(original[u]),du@rot(s.ref[u]),w)*np.linalg.norm(original[u,:3,:3],axis=0)
    p[l,:3,3]=E;p[l,:3,:3]=blend(fore_swing@rot(original[l]),neutral@rot(s.ref[l]),w)*np.linalg.norm(original[l,:3,:3],axis=0)
    for prefix,parent,axis0,driver,swing in [('upperarm',u,ru,du,upper_swing),('lowerarm',l,rf,neutral,fore_swing)]:
        for suffix in ['01','02']:
            j=s.ids[prefix+'_twist_'+suffix+'_r'];offset=s.ref[j,:3,3]-s.ref[parent,:3,3]
            station=offset@axis0/(axis0@axis0)
            target_driver=driver if prefix=='upperarm' else turn(fore,roll*np.clip(station/(2/3),0,1))@driver
            p[j,:3,:3]=blend(swing@rot(original[j]),target_driver@rot(s.ref[j]),w)*np.linalg.norm(original[j,:3,:3],axis=0)
            p[j,:3,3]=(p[parent]@s.relative(s.ref[parent],s.ref[j]))[:3,3]
    clav=s.ids['clavicle_r'];native=s.relative(s.ref[clav],s.ref[u])
    p[clav,:3,3]=A-p[clav,:3,:3]@native[:3,3]
    return p,A,E,H,s.unit(palm@rf),roll

def main():
    knots=list(range(0,len(times),2));controls=[];rolls=[];previous=np.zeros(4);reference=0.
    lower=np.array([-14.,-14.,-18.,-.85]);upper=-lower
    for i in knots:
        if active[i]<1e-8:
            controls.append(np.zeros(4));reference=pose(i,controls[-1],reference)[-1]
            rolls.append(reference);previous=controls[-1].copy();continue
        a_base=source[i,u,:3,3];e_base=source[i,l,:3,3];guess=np.clip(previous,lower+1e-6,upper-1e-6)
        def residual(x):
            p,a,e,h,wrist_axis,roll=pose(i,x,reference)
            cut=points(p,CUT,i);arm=points(p,ARM,i)
            opening=np.maximum(0.,cut@corner_normal+corner_margin)*s.ease(0,5,cut[:,0])
            eye=np.maximum(0.,14.-np.linalg.norm(arm,axis=1))
            return np.r_[opening/.055,eye/.35,(s.unit(h-e)-wrist_axis)/.30,
                (a-a_base)/np.array([7.,7.,9.]),(e-e_base)/8.,x[3]/.55,
                (x-guess)/np.array([3.,3.,3.,.35]),max(0.,abs(roll)-np.radians(110))/np.radians(12.),max(0.,e[2]-h[2]+1.)/5.]
        solved=least_squares(residual,guess,bounds=(lower,upper),max_nfev=65,ftol=2e-5,xtol=2e-5,gtol=2e-5)
        controls.append(solved.x);previous=solved.x;reference=pose(i,solved.x,reference)[-1];rolls.append(reference)
    dense=PchipInterpolator(times[knots],controls,axis=0)(times);roll_dense=PchipInterpolator(times[knots],rolls)(times)
    result=np.array([pose(i,x,roll_dense[i])[0] for i,x in enumerate(dense)])
    result[0]=source[0];result[-1]=source[-1]
    spec=importlib.util.spec_from_file_location('r4_encoder',R4/'author.py')
    encoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(encoder);encoder.O=O
    out={};details={}
    for family in data.files:
        original=data[family];assert np.max(abs(original[:,write]-source[:,write]))<1e-7
        edited=original.copy();edited[:,write]=result[:,write];out[family]=edited
        encoder.write_profile(json.loads((R4/'SavedReadback'/f'{family}.json').read_text()),edited,family)
        fixed=[j for j in range(len(s.names)) if j not in write]
        details[family]={'immutable_component_transform_error':float(abs(edited[:,fixed]-original[:,fixed]).max()),
            'maximum_native_offset_error_cm':max(max(s.offsets(p).values()) for p in edited),
            'maximum_shoulder_shift_cm':float(np.linalg.norm(edited[:,u,:3,3]-original[:,u,:3,3],axis=1).max())}
    np.savez_compressed(O/'poses.npz',**out)
    (O/'authoring.json').write_text(json.dumps({'method':'M870 R3 shared anatomical skin hinge and shoulder/pole constraints, SVD helpers and native lengths',
        'controls':dense.tolist(),'forearm_roll':roll_dense.tolist(),'families':details,'write_bones':[s.names[j] for j in write]},indent=2))
    print('R5_ELBOW_AUTHORED',details,flush=True)

if __name__=='__main__':main()
