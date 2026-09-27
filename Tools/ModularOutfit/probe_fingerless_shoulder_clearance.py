"""Anatomical arm IK with a fixed hand and unchanged segment lengths; candidate only."""
import json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';arm={};thumb={}
exec((P/'Tools/ModularOutfit/solve_fingerless_cuff_arm_clearance.py').read_text().split('manifest=[]')[0],arm)
exec((P/'Tools/ModularOutfit/solve_fingerless_thumb_cuff_clearance.py').read_text().split('files=')[0],thumb)
mx=arm['mx'];d=json.loads((R/'ClearanceAfter/A762__base_reload_empty_poses.json').read_text());gd=json.loads((R/'ClearanceAfter/A762_glove.json').read_text());ids={b['index']:n for n,b in gd['bones'].items()};parents={n:ids.get(b['parent']) for n,b in gd['bones'].items()}
def solve(bones,axis,clavicle_angle,elbow_angle):
    c=mx(bones['clavicle_r']);upper=mx(bones['upperarm_r']);lower=mx(bones['lowerarm_r']);hand=mx(bones['hand_r']);s=upper[:3,3];e=lower[:3,3];h=hand[:3,3]
    cnew=c.copy();cnew[:3,:3]=c[:3,:3]@np.asarray(Matrix.Rotation(math.radians(clavicle_angle),3,Vector(axis)));dc=cnew@np.linalg.inv(c);new_s=(dc@np.r_[s,1])[:3]
    l1=np.linalg.norm(e-s);l2=np.linalg.norm(h-e);v=h-new_s;distance=np.linalg.norm(v)
    if distance>=l1+l2-1e-8 or distance<=abs(l1-l2)+1e-8:return None
    v/=distance;x=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-x*x));pole=e-new_s;pole-=v*(pole@v);pole/=np.linalg.norm(pole);pole=np.asarray(Matrix.Rotation(math.radians(elbow_angle),3,Vector(v)))@pole;new_e=new_s+x*v+height*pole
    ru=arm['between'](e-s,new_e-new_s);rl=arm['between'](h-e,h-new_e);du=np.eye(4);du[:3,:3]=ru;du[:3,3]=new_s-ru@s;dl=np.eye(4);dl[:3,:3]=rl;dl[:3,3]=new_e-rl@e
    result={}
    for n,b in bones.items():
        chain=[];bn=n
        while bn in parents:chain.append(bn);bn=parents[bn]
        change=np.eye(4) if 'hand_r' in chain else dl if 'lowerarm_r' in chain else du if 'upperarm_r' in chain else dc if 'clavicle_r' in chain else np.eye(4)
        result[n]=arm['pack'](change@mx(b))
    return result
results=[]
for i,p in enumerate(d['poses']):
    before=thumb['evaluate'](p['bones'])
    if before<=.03:continue
    best=before;choice=None
    for angle,axis,elbow in [(a,axis,e) for a in (5,10,15,20,25,30) for axis in ([0,1,0],[0,-1,0],[0,0,1],[0,0,-1],[1,0,0],[-1,0,0]) for e in (0,15,-15,30,-30,45,-45,60,-60)]:
        candidate=solve(p['bones'],axis,angle,elbow)
        if candidate is None:continue
        score=thumb['evaluate'](candidate)
        if score<best:best=score;choice=dict(axis=axis,clavicle_angle=angle,elbow_angle=elbow,bones=candidate)
        if best<=.005:break
    print('SHOULDER_IK_PROBE',i,before,best,{k:v for k,v in choice.items() if k!='bones'} if choice else None,flush=True);results.append(dict(index=i,before=before,after=best,choice=choice))
(R/'ClearanceAfter/shoulder-ik-probe.json').write_text(json.dumps(results,separators=(',',':')))
