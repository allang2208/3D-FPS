"""Adapt the project's relaxed resident loop to Meshy's 24-joint, fingerless biped."""
import json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/'Tools/VillageTavernKeeper/Idle'))
from retarget_idle import bake,forward_kinematics,DONOR

def fit(reference):
    original=reference['names'];aliases={'Hips':'pelvis','Spine02':'spine_01','Spine01':'spine_02','Spine':'spine_03','neck':'neck_01','Head':'head'}
    for side,suffix in [('Left','_l'),('Right','_r')]:
        for name,standard in [('Shoulder','clavicle'),('Arm','upperarm'),('ForeArm','lowerarm'),('Hand','hand'),('Foot','foot'),('ToeBase','ball')]:
            aliases[side+name]=standard+suffix
    names=[aliases.get(n,n) for n in original];rest=list(reference['reference']);parents=list(reference['parents'])
    world=forward_kinematics(np.asarray(rest),parents)
    # Use the forearm direction as a temporary palm target for the donor solver.
    # Virtual landmarks never enter the exported skeleton or animation.
    for side in ('_l','_r'):
        if 'middle_01'+side in names:continue
        wrist=names.index('hand'+side);elbow=names.index('lowerarm'+side)
        direction=world[wrist,:3,3]-world[elbow,:3,3]
        delta=np.linalg.solve(world[wrist,:3,:3],direction/np.linalg.norm(direction)*5.3)
        names.append('middle_01'+side);parents.append(wrist);rest.append([*delta,0,0,0,1,1,1,1])
    motion=bake(dict(names=names,parents=parents,reference=rest),json.loads(DONOR.read_bytes()))
    motion['tracks']={original[names.index(n)]:v for n,v in motion['tracks'].items()}
    return motion
if __name__=='__main__':
    source,target=map(Path,sys.argv[1:3])
    target.write_text(json.dumps(fit(json.loads(source.read_bytes())),separators=(',',':')))
