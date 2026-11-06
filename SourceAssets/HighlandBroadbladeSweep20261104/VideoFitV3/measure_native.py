from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent
OBS=np.array(json.loads((HERE/'screen-tracks.json').read_text())['tracks']); F=90/np.tan(np.deg2rad(37.5))

def projected(points):return np.column_stack([160-F*points[:,0]/points[:,1],90+F*points[:,2]/points[:,1]])
def unit(points):return points/np.linalg.norm(points,axis=1,keepdims=True)
def section_radius(vertices,axis):
    centered=vertices-vertices.mean(axis=0);radial=centered-np.outer(centered@axis,axis)
    return np.linalg.svd(radial,compute_uv=False)[1]/np.sqrt(len(vertices))

report={}
for case in ['StandardIdleEntry','LongGripIdleEntry','Standard','LongGrip']:
 folder=HERE.parent/'Review/VideoFitV3'/case;data=json.loads((folder/'surface.json').read_text(encoding='utf-8-sig'));frames=data['frames'];names=np.array(data['bone_names'])[np.fromfile(folder/'arms.mainbone',np.uint16)];skin=[np.fromfile(folder/f'f{i:04}.vertices',np.float32).reshape(-1,3) for i in range(len(frames))];r={};blade=np.fromfile(folder/'part0.vertices',np.float32).reshape(-1,3);near=[]
 for f in frames:
    w=f['weapon'];v=R.from_quat(w['q']).apply(blade)+w['p'];near.append(np.linalg.norm(v,axis=1).min())
 r['blade_nearest_eye_cm']=round(float(min(near)),2);r['blade_nearest_frame']=int(np.argmin(near));r['confirmed_hit']=data.get('contact_probe');r['no_hit_view_turn_max_deg']=float(max(np.linalg.norm(f['camera_rotation_pyr']) for f in frames))
 for s,side in enumerate(['r','l']):
    coords=lambda n:np.array([f['bones'][n+'_'+side]['p'] for f in frames]);e=coords('lowerarm');h=coords('hand');m=coords('middle_01');forearm=unit(h-e);bend=np.rad2deg(np.arccos(np.clip((forearm*unit(m-h)).sum(1),-1,1)));op=OBS[:,s*2:s*2+2];vis=((op>[1,1])&(op<[319,179])).all(1);err=np.linalg.norm(projected(h[::2])-op,axis=1);rel={}
    ids=np.char.startswith(names,'lowerarm') & np.char.endswith(names,'_'+side);along=(skin[-1]-e[-1])@forearm[-1]/np.linalg.norm(h[-1]-e[-1]);
    for t in [.38,.56,.72,.85]:
        ring=np.flatnonzero(ids & (abs(along-t)<.055));base=section_radius(skin[-1][ring],forearm[-1]);values=[section_radius(v[ring],forearm[i])/base for i,v in enumerate(skin)];rel[str(t)]=[round(float(min(values)),2),int(np.argmin(values))]
    r[side]=dict(visible_wrist_median_px_at_320=round(float(np.median(err[vis])),2),visible_wrist_p90_px_at_320=round(float(np.percentile(err[vis],90)),2),max_bend_deg=round(float(bend.max()),1),max_bend_frame=int(np.argmax(bend)),cross_section_min_ratio_frame=rel)
 report[case]=r
(HERE/'native-readback.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
