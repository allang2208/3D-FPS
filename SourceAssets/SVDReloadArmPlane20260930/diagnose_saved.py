"""Requested SVD arm and matched-chainmail diagnosis on saved compressed poses."""
import sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

P=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write,digest,asset_file
from garment_motion import matrix,prepare,posed
from diagnose_chainmail_camera import correct,camera_frame,intrusion

def unit(v):return v/max(np.linalg.norm(v),1.e-12)
def roll(pose,rest):
    u,l,h=[pose[n] for n in ('upperarm_l','lowerarm_l','hand_l')]
    ru,rl,rh=[rest[n] for n in ('upperarm_l','lowerarm_l','hand_l')]
    ud,ld=unit(l[:3,3]-u[:3,3]),unit(h[:3,3]-l[:3,3])
    rp=unit(np.cross(rl[:3,3]-ru[:3,3],rh[:3,3]-rl[:3,3]))
    pl=unit(np.cross(ud,ld))
    old=Rotation.from_matrix(u[:3,:3]).as_matrix()@Rotation.from_matrix(ru[:3,:3]).as_matrix().T@rp
    return float(np.degrees(np.arctan2(np.dot(ud,np.cross(old,pl)),np.dot(old,pl)))),float(np.degrees(np.arccos(np.clip(ud@ld,-1,1))))

def main():
    root=P/'SourceAssets/ChainmailCameraClearance20260929/SVD'
    before=read(root/'poses.json');after=read(O/'compressed-poses.json')
    if digest(asset_file(after['native']))!=after['native_sha256']:raise RuntimeError('Native mesh changed')
    for path,sha in after['clips'].items():
        if digest(asset_file(path))!=sha:raise RuntimeError('Clip changed '+path)
    garments=[read(root/f'LOD{i}.json') for i in range(3)]
    bare=read(O/'bare-current.json');skin_data=prepare(bare)
    for d in garments+[bare]:
        if digest(asset_file(d['source']))!=d['asset_sha256']:raise RuntimeError('Resample mesh '+d['source'])
    data=[prepare(d) for d in garments];d=garments[0]
    rest={n:matrix(t) for n,t in d['rest'].items()}
    shell=set(np.array(d['triangles'])[np.array(d['materials'])==0].flat)
    ids=np.array([i for i,w in enumerate(d['weights']) if i in shell and sum(v for n,v in w.items() if n.endswith('_l') and n.startswith(('upperarm','lowerarm')))> .95])
    skin=trimesh.Trimesh(bare['positions'],bare['triangles'],process=False)
    closest,_,tri=trimesh.proximity.closest_point(skin,np.array(d['positions'])[ids])
    triangles=np.array(bare['triangles'])[tri]
    bary=trimesh.triangles.points_to_barycentric(skin.triangles[tri],closest)
    edges=[]
    for garment in garments:
        faces=np.array(garment['triangles']);p=np.array(garment['positions'])
        left=np.array([sum(v for n,v in w.items() if n.endswith('_l'))>.95 for w in garment['weights']])
        faces=faces[np.all(left[faces],axis=1)]
        e=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
        edges.append((e,np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)))
    upper=np.array([i for i,w in enumerate(d['weights']) if sum(v for n,v in w.items() if n.startswith(('upperarm','clavicle')))> .65])
    lookup={(r['clip'],r['time']):r for r in before['poses']}
    rows=[]
    for sample in after['poses']:
        old={n:matrix(t) for n,t in lookup[(sample['clip'],sample['time'])]['bones'].items()}
        new={n:matrix(t) for n,t in sample['bones'].items()}
        immutable=[n for n in old if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_','WPN_')) or n.endswith('_r')]
        row=dict(clip=sample['clip'],time=sample['time'],hand_weapon_position_delta_cm=max(float(np.linalg.norm(old[n][:3,3]-new[n][:3,3])) for n in immutable),
            hand_weapon_rotation_delta_deg=max(float(np.degrees((Rotation.from_matrix(old[n][:3,:3]).inv()*Rotation.from_matrix(new[n][:3,:3])).magnitude())) for n in immutable))
        for label,bones in [('before',old),('after',new)]:
            frame=camera_frame(bones,'hip');bones,_=correct(bones,frame)
            points=posed(data[0],bones)
            surface=posed(skin_data,bones)[triangles]
            normals=np.cross(surface[:,2]-surface[:,0],surface[:,1]-surface[:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1.e-12)
            distance=np.sum((points[ids]-np.sum(surface*bary[:,:,None],axis=1))*normals,axis=1)
            lods=[]
            for prepared,(edge,length) in zip(data,edges):
                pp=posed(prepared,bones);current=np.linalg.norm(pp[edge[:,0]]-pp[edge[:,1]],axis=1)
                lods.append(dict(max_edge_cm=float(current.max()),max_stretch=float((current[length>.1]/length[length>.1]).max())))
            angle,flex=roll(bones,rest)
            row[label]=dict(upper_roll_deg=angle,flex_deg=flex,upper_intrusion=intrusion(points,frame,upper),
                sleeve_min_corresponding_clearance_cm=float(distance.min()),sleeve_p01_clearance_cm=float(np.percentile(distance,1)),sleeve_below_zero=int(np.sum(distance<0)),lods=lods)
        rows.append(row)
    tail=[r for r in rows if 2.<=r['time']<=344/120]
    summary=dict(samples=len(rows),tail_samples=len(tail),
        max_contact_position_delta_cm=max(r['hand_weapon_position_delta_cm'] for r in rows),max_contact_rotation_delta_deg=max(r['hand_weapon_rotation_delta_deg'] for r in rows),
        before_max_tail_upper_roll_deg=max(abs(r['before']['upper_roll_deg']) for r in tail),after_max_tail_upper_roll_deg=max(abs(r['after']['upper_roll_deg']) for r in tail),
        before_min_tail_flex_deg=min(r['before']['flex_deg'] for r in tail),after_min_tail_flex_deg=min(r['after']['flex_deg'] for r in tail),
        after_upper_intrusion_samples=sum(r['after']['upper_intrusion']>0 for r in rows),
        garment_asset=d['source'],garment_sha256=d['asset_sha256'],game_tested=False,
        limitation='20 Hz compressed pose samples, current shared clearance model, bind-corresponding shell-to-skin distance excludes cuff/lining and WPO; not a global collision or runtime visual acceptance')
    for label in ('before','after'):
        summary[label]=dict(min_clearance_cm=min(r[label]['sleeve_min_corresponding_clearance_cm'] for r in rows),min_p01_clearance_cm=min(r[label]['sleeve_p01_clearance_cm'] for r in rows),max_below_zero=max(r[label]['sleeve_below_zero'] for r in rows),
            lod_max_edge_cm=[max(r[label]['lods'][lod]['max_edge_cm'] for r in rows) for lod in range(3)],lod_max_stretch=[max(r[label]['lods'][lod]['max_stretch'] for r in rows) for lod in range(3)])
    write(O/'saved-arm-chainmail-diagnosis.json',dict(summary=summary,rows=rows))
    print(summary)

if __name__=='__main__':main()
