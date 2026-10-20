"""Move the right support chain sideways around the fixed pistol grip.

The native segment lengths, local joint stations, hand shape, weapon transform
and contact clock are retained. The SVCH stock is wider than the SVD source.
"""
from pathlib import Path
import sys,json,copy,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_surfaces import *
from scipy.ndimage import gaussian_filter1d
from action_framing import camera_for_frame
O=HERE
cached=O/'poses-preclearance.npz'
if not cached.exists():cached.write_bytes((O/'poses.npz').read_bytes())
source=np.load(cached);output={k:source[k].copy() for k in source.files}
chain=[j for j,n in enumerate(names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm'))]
li,hi,root=[ids[n] for n in ('lowerarm_r','hand_r','WPN_root')]
axis=rigid(ref[li])[:3,:3].T@unit(ref[hi,:3,3]-ref[li,:3,3])
rel=rigid(ref[li])[:3,:3].T@rigid(ref[hi])[:3,:3]
clip=motion['clips']['quick_melee'];times=np.array(clip['times'])
# The approved mesh has open shoulder cuts. Use those actual boundary vertices
# to place the upper-arm root outside the camera, without stretching the mesh.
edges=np.sort(np.vstack([bare.T[:,[0,1]],bare.T[:,[1,2]],bare.T[:,[2,0]]]),axis=1)
edges,counts=np.unique(edges,axis=0,return_counts=True)
boundary=bare.first[np.unique(edges[counts==1])]
dominant=[names[j] for j in bare.weights.argmax(1)]
root_vertices=np.array([j for j in boundary if dominant[j].startswith(('upperarm','clavicle')) and dominant[j].endswith('_r')])
fixture=json.loads((O/'native-candidate.json').read_text())['families'][0]
camera=matrices([fixture['view_to_camera']])[0]
tx=np.tan(np.radians(fixture['camera_horizontal_fov']/2));ty=tx/fixture['camera_aspect']
upper=[j for j in chain if not names[j].startswith('lowerarm')]
report={}
for family in ['base','angled','vertical','canted','prism']:
    poses=output[family]
    dx=[]
    for q in poses:
        e=np.linalg.inv(q[root])@np.r_[q[li,:3,3],1]
        dx.append(min(0.,(-.108-e[0])*100))
    # Smooth the clearance envelope without weakening the required clearance.
    dx=np.minimum(dx,gaussian_filter1d(dx,1.5))
    for i,q in enumerate(poses):
        w=ease(0,.045,times[i])*(1-ease(.8,.9,times[i]))
        H=q[hi,:3,3].copy();D=q[li,:3,3]-H
        target=D+rigid(q[root])[:3,:3]@np.array([dx[i]*w,0,0])
        turn=swing(D,target)
        shift=turn@D-D
        for j in chain:
            if names[j].startswith('lowerarm'):
                q[j,:3,3]=H+turn@(q[j,:3,3]-H);q[j,:3,:3]=turn@q[j,:3,:3]
            else:
                # Preserve the approved upper-arm direction. Rotating the
                # entire shoulder around the hand exposed the cut arm root.
                q[j,:3,3]+=shift
    needed=[];axes=[]
    for fi,q in enumerate(poses):
        points=bare.evaluate(q)[root_vertices]
        cameras=[camera,camera_for_frame(camera,fi)];visible=np.zeros(len(points),bool);planes=[]
        for view in cameras:
            cp=points@view[:3,:3].T+view[:3,3]
            visible|=(cp[:,0]>1)&(abs(cp[:,1])<cp[:,0]*tx)&(abs(cp[:,2])<cp[:,0]*ty)
            n=-view[0,:3];d=-view[0,3]
            planes.append((n/np.linalg.norm(n),d/np.linalg.norm(n)))
        plane=unit(sum(n for n,d in planes))
        E=q[li,:3,3];S=q[ids['upperarm_r'],:3,3]
        ax=unit(np.cross(S-E,plane));axes.append(ax)
        def outside(degrees):
            turn=R.from_rotvec(ax*np.radians(degrees)).as_matrix()
            moved=E+(points-E)@turn.T
            return all(float(np.min(moved@n+d))>.4 for n,d in planes)
        if not visible.any():needed.append(0.);continue
        if not outside(40):raise RuntimeError('Cannot keep shoulder cut outside view within the local arm adjustment at frame '+str(len(needed)))
        a,b=0.,40.
        for _ in range(16):
            mid=(a+b)/2
            if outside(mid):b=mid
            else:a=mid
        needed.append(b)
    needed=np.maximum(needed,gaussian_filter1d(needed,1.5))
    for i,q in enumerate(poses):
        E=q[li,:3,3];turn=R.from_rotvec(axes[i]*np.radians(needed[i])).as_matrix()
        for j in upper:q[j,:3,3]=E+turn@(q[j,:3,3]-E);q[j,:3,:3]=turn@q[j,:3,:3]
    rolls=[]
    for q in poses:
        v=R.from_matrix(rigid(q[li])[:3,:3].T@rigid(q[hi])[:3,:3]@rel.T).as_quat()
        if v[3]<0:v=-v
        rolls.append(2*np.arctan2(v[:3]@axis,v[3]))
    rolls=np.unwrap(rolls)
    for i,q in enumerate(poses):
        if i in (0,len(poses)-1):continue
        for prefix,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
            j=ids[prefix+'_r'];r=rigid(ref[li])[:3,:3].T@rigid(ref[j])[:3,:3]
            q[j,:3,:3]=rigid(q[li])[:3,:3]@R.from_rotvec(axis*rolls[i]*share).as_matrix()@r*np.linalg.norm(q[j,:3,:3],axis=0)
    profile=json.loads((O/'Profiles'/(family+'.json')).read_text())
    entry=next(c for c in profile['clips'] if c['base']==clip['path']);tracks=[]
    for j,n in enumerate(names):
        values=[]
        for i,q in enumerate(poses):
            loc=relative(q[parents[j]],q[j]) if parents[j]>=0 else q[j];raw=np.array(clip['frames'][i][j]);v=np.zeros(10)
            v[:3]=loc[:3,3]-raw[:3];v[3:7]=(R.from_matrix(rigid(loc)[:3,:3])*R.from_quat(raw[3:7]).inv()).as_quat();v[7:]=np.linalg.norm(loc[:3,:3],axis=0)-raw[7:]
            if values and values[-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values.append(v)
        ar=np.array(values)
        if np.max(abs(ar-np.array([0,0,0,0,0,0,1,0,0,0])))>1e-7:tracks.append({'bone':n,'times':times.tolist(),'values':np.round(ar,10).ravel().tolist()})
    entry['tracks']=tracks
    (O/'Profiles'/(family+'.json')).write_text(json.dumps(profile,separators=(',',':')))
    sig=np.array([driver.signature(matrix_pose(q),'r') for q in poses])
    report[family]={'maximum_elbow_move_cm':float(np.linalg.norm(poses[:,li,:3,3]-source[family][:,li,:3,3],axis=1).max()),
                    'wrist_flex_dev_peak_deg':np.max(np.abs(sig[:,1:3]),axis=0).tolist(),
                    'maximum_upper_arm_root_clearance_rotation_deg':float(max(needed))}
np.savez_compressed(O/'poses.npz',**output)
(O/'stock-clearance-authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
