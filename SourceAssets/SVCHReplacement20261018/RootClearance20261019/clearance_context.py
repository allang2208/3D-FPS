"""Current V9 surface and accepted SVCH reload camera frame for authoring."""
from arm_math import *
from collections import Counter
from scipy.interpolate import PchipInterpolator
ref=matrices(arms['reference'])
ci,ui,li,hi=[ids[n] for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l')]
axis0=unit(ref[li,:3,3]-ref[ui,:3,3]);long0=np.linalg.norm(ref[li,:3,3]-ref[ui,:3,3])
station=(V-ref[ui,:3,3])@axis0/long0
# Weld only to identify the actual cut edge; keep the approved mesh untouched.
_,weld=np.unique(np.round(V,5),axis=0,return_inverse=True)
tris=weld[np.asarray(arms['triangles'])]
edges=Counter(tuple(sorted((int(t[i]),int(t[(i+1)%3])))) for t in tris for i in range(3) if t[i]!=t[(i+1)%3])
boundary=np.unique([v for e,count in edges.items() if count==1 for v in e])
rim=np.intersect1d(np.flatnonzero(np.isin(weld,boundary)),upper)
rootband=np.unique(np.r_[upper[station[upper]<.22],rim])
capture=O.parents[2]/'Saved/SVCHPoseAudit/svch-left-reload-20261019-before'
rows=[json.loads(x) for x in (capture/'handoff.jsonl').read_text().splitlines()]
curves={}
for role,stage in [('reload','normal'),('reload_empty','empty')]:
    rr=[r for r in rows if r['stage']==stage and r['reloading'] and r['action_alpha']>.99]
    rr=sorted({r['source_time']:r for r in rr}.values(),key=lambda r:r['source_time'])
    times=np.array([r['source_time']*120 for r in rr])
    curves[role]=(times,PchipInterpolator(times,np.array([r['component_location']+r['component_rotation'] for r in rr]),axis=0))
# The current camera maintains vertical FOV. A root hidden only at the left
# edge of a 16:9 capture can reappear in a wider user window.
ty=np.tan(np.deg2rad(75*.5))
def cam_at(role,frame):
    t,curve=curves[role];v=curve(np.clip(frame,t[0],t[-1]));return camera_transform(v[:3],v[3:])
def root_points(p,cam):return transform(cam,skin(p,rootband))
def screen_margin(points,aspect=16/9):
    depth=np.maximum(points[:,0],.001)
    margin=np.maximum(abs(points[:,1])/(depth*ty*aspect),abs(points[:,2])/(depth*ty))-1
    margin[points[:,0]<1.]=2
    return margin
def proximal_roll(p,angle):
    """Rigidly turn proximal support around unchanged elbow-to-wrist axis."""
    out=p.copy();E,H=p[li,:3,3],p[hi,:3,3];axis=unit(H-E);r=R.from_rotvec(axis*np.deg2rad(angle));T=np.eye(4);T[:3,:3]=r.as_matrix();T[:3,3]=E-r.apply(E)
    for j,n in enumerate(names):
        if n=='clavicle_l' or (n.endswith('_l') and n.startswith('upperarm')) or n=='lowerarm_l':out[j]=T@p[j]
    j=ids['lowerarm_twist_02_l'];out[j,:3,:3]=R.from_rotvec(axis*np.deg2rad(angle*.5)).as_matrix()@p[j,:3,:3]
    return out
if __name__=='__main__':
    report={'current_arms_sha256':arms['sha256'],'root_vertices':len(rootband),'rim_vertices':len(rim),'camera':'same source-clock action framing; current vertical FOV 75 deg','clips':{}}
    for role in ('reload','reload_empty'):
        samples=[]
        for i in range(0,len(motion['clips'][role]['times']),8):
            p=pose(role,i);cam=cam_at(role,i);pts=root_points(p,cam)
            choices=[]
            for a in range(-25,26,5):
                q=proximal_roll(p,a);pr=root_points(q,cam);m=screen_margin(pr,21/9)
                choices.append((float(m.min()),a))
            samples.append({'frame':i,'visible169':int((screen_margin(pts)<0).sum()),'visible_wide':int((screen_margin(pts,21/9)<0).sum()),'root_cam_bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'best_roll':max(choices)})
        report['clips'][role]=samples
        relevant=[r for r in samples if r['visible_wide']]
        print(role,'visible_samples',len(relevant),'rows',json.dumps(relevant[::max(1,len(relevant)//6)]),flush=True)
    (O/'baseline_geometry.json').write_text(json.dumps(report,indent=2))
