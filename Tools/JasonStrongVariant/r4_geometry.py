"""Build sparse corrective forms in Jason's bind space; all lengths are cm."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from muscle_shape import groups_for_bones
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117')
R3=BASE/'R3_ArmsRefined'
OUT=BASE/'R4_PoseRefined'

def smooth(a,b,x):
    u=np.clip((x-a)/(b-a),0,1)
    return u*u*(3-2*u)

def author():
    mesh=json.loads((R3/'AnatomyReview/derived_saved_mesh.json').read_text())
    native=json.loads((R3/'body_source.json').read_text())
    p=np.array(native['positions'])
    x,y,z=p.T
    bones={b['name']:np.array(b['position']) for b in native['bones']}
    seam=np.asarray(json.loads((R3/'neck_seam.json').read_text()))
    samples=np.concatenate([seam[:,0]+t*(seam[:,1]-seam[:,0]) for t in np.linspace(0,1,12)])
    protection=smooth(.8,4.2,cKDTree(samples).query(p)[0])
    groups=groups_for_bones(native['bones'])
    def group_weight(names):
        return np.asarray([sum(w for i,w in ws if groups[i] in names) for ws in native['weights']])
    torso=group_weight({'torso'})
    # Flow from the upper pectoral into a shallow deltopectoral groove.
    diagonal=13.0+.34*(136.-z)
    chest=np.zeros_like(p)
    chest[:,1]=torso*smooth(1.5,6,y)*protection*(
        .48*np.exp(-((abs(x)-8.7)/5.7)**2-((z-133.8)/5.5)**2)
        -.36*np.exp(-((abs(x)-diagonal)/2.25)**2-((z-132.3)/6.2)**2))
    forms={}
    for side,sgn in [('l',1.),('r',-1.)]:
        shoulder=bones['upperarm_'+side]
        elbow=bones['lowerarm_'+side]
        axis=elbow-shoulder
        along=(p-shoulder)@axis/(axis@axis)
        radial=p-shoulder-along[:,None]*axis
        axis/=np.linalg.norm(axis)
        front=np.array([0.,1.,0.])-axis*axis[1]
        front/=np.linalg.norm(front)
        rf=radial@front
        arm=group_weight({'upperarm_'+side,'lowerarm_'+side})
        front_mask=smooth(-.3,3.2,rf)
        # Mid-belly moves anteriorly and slightly proximally on flexion.
        belly=np.exp(-((along-.51)/.244)**2)*front_mask*arm*protection
        belly*=smooth(.04,.20,along)*(1-smooth(.76,.96,along))
        bulge=(.96*front-.27*axis)[None,:]*belly[:,None]
        flank=radial-rf[:,None]*front
        bulge+=.042*belly[:,None]*flank
        forms['R4_Biceps_'+side]=bulge
        # Relax the superior cap and spread its inner slope toward the neck on elevation.
        lateral=(x-shoulder[0])*sgn
        cap=smooth(1.,6.,lateral)*np.exp(-((along-.32)/.45)**2-((y-shoulder[1])/8.5)**2)
        cap*=arm*protection*smooth(122.,132.,z)*(1-smooth(.56,.83,along))
        forms['R4_Shoulder_'+side]=cap[:,None]*np.array([-.91*sgn,0.,.28])
    positions=np.asarray(mesh['positions'])+chest
    def sparse(delta):
        ids=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-5)
        return [[int(i),*delta[i].tolist()] for i in ids]
    result={'base':positions.tolist(),'targets':{n:sparse(d) for n,d in forms.items()}}
    (OUT/'Review/forms.json').write_text(json.dumps(result,separators=(',',':')))
    print('R4_FORMS',[(n,len(d)) for n,d in result['targets'].items()])
if __name__=='__main__':author()
