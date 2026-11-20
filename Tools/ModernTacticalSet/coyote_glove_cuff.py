"""Measure the equipped M870 glove's proximal band against the actual shirt cuff."""
import gzip
import json

import numpy as np

from coyote_glove_pose_review import REVIEW,SET,read
from native_glove_review import Skin,component


def main():
    path=REVIEW/"Read/Super90.json";data=read(path)
    shirt_path=REVIEW/"Read/Super90_Shirt.json"
    shirt=read(shirt_path);pose_path=SET/"NativeGloveR1/Read/M870_poses.json.gz"
    pose=json.load(gzip.open(pose_path,"rt"))
    names=pose["names"];parents=[names.index(p) if p in names else -1 for p in pose["parents"]]
    glove=Skin(data,names,False);cuff=Skin(shirt,names,False)
    cloth=np.unique(cuff.faces[cuff.mats==shirt["material_slots"].index("CombatCuff")])
    lining=np.unique(glove.faces[glove.mats==data["material_slots"].index("CG_Stretch")])
    rings=[]
    for side in ("r","l"):
        h=names.index("hand_"+side);e=names.index("lowerarm_"+side)
        wrist=np.array(data["bones"][names[h]]["position"])
        axis=np.array(data["bones"][names[e]]["position"])-wrist;axis/=np.linalg.norm(axis)
        radial=np.cross(axis,np.eye(3)[np.argmin(np.abs(axis))]);radial/=np.linalg.norm(radial)
        circum=np.cross(axis,radial)
        def sectors(skin,ids,radius):
            d=skin.points[ids]-wrist;good=np.linalg.norm(d,axis=1)<radius
            d=d[good];ids=ids[good]
            section=((np.arctan2(d@circum,d@radial)+np.pi)*16/(2*np.pi)).astype(int)%16
            return [ids[section==i] for i in range(16)]
        pairs=list(zip(sectors(cuff,cloth,15),sectors(glove,lining,10.7)))
        if any(not len(a) or not len(b) for a,b in pairs):
            raise ValueError(f"Incomplete band sampling around the {side} wrist")
        rings.append((h,e,pairs))
    output={}
    for key,clip in pose["clips"].items():
        minimum=np.inf;gaps=0;samples=0
        for frame in clip["local"]:
            mat=component(frame,parents);cp=cuff.skin(mat);gp=glove.skin(mat)
            for h,e,pairs in rings:
                axis=mat[e,:3,3]-mat[h,:3,3];axis/=np.linalg.norm(axis)
                for a,b in pairs:
                    overlap=np.max(gp[b]@axis)-np.min(cp[a]@axis)
                    minimum=min(minimum,overlap);gaps+=int(overlap<0);samples+=1
        output[key]=dict(frames=len(clip["local"]),sector_samples=samples,gaps=gaps,minimum_axial_overlap_mm=round(float(minimum)*10,3))
    (REVIEW/"M870-cuff-overlap.json").write_text(json.dumps(dict(glove_sha=data["asset_sha256"],shirt_sha=shirt["asset_sha256"],
        method="Distance along the live forearm axis between the front-most shirt cuff and rear-most glove lining, 16 corresponding sectors at each wrist. Offline sampled LBS; this measures overlap along the wrist, not render occlusion.",
        clips=output),indent=2))
    print("M870 glove/sleeve",sum(v["sector_samples"] for v in output.values()),sum(v["gaps"] for v in output.values()),
          min(v["minimum_axial_overlap_mm"] for v in output.values()),flush=True)


if __name__=="__main__":
    main()
