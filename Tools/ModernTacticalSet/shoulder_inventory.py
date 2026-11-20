"""Make the editable male/female body pieces and the matching inventory geometry."""
from pathlib import Path
import sys
import json

import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).parent))
import combat4_sources as studio
from shirt_geometry import merge

R4=studio.R
OUT=studio.S/"ShoulderFit20261118"
studio.R=OUT
studio.iconns["OUT"]=OUT/"Icons"
for folder in ("Models","Exports","Icons"):
    (OUT/folder).mkdir(exist_ok=True)


def patch_part(rig, filename, label):
    d=studio.read(R4/"Authored"/f"{filename}_{rig}.json")
    edits=np.load(OUT/f"{rig}-{label}.npz")
    key=lambda p: np.asarray(p,dtype="<f4").tobytes()
    mapping={key(a):b for a,b in zip(edits["before"],edits["after"])}
    old=np.asarray(d["positions"])
    p=np.array([mapping.get(key(q),q) for q in old])
    f=np.asarray(d["triangles"])
    moved=(p!=old).any(axis=1)
    affected=moved[f].any(axis=1)
    face=f[affected]
    new_face=-np.cross(p[face[:,1]]-p[face[:,0]],p[face[:,2]]-p[face[:,0]])
    n=np.asarray(d["normals"])
    old_group=np.column_stack((face.flatten(),np.round(n[affected].reshape(-1,3),5)))
    _,idx=np.unique(old_group,axis=0,return_inverse=True)
    sums=np.zeros((int(idx.max())+1,3))
    np.add.at(sums,idx,new_face.repeat(3,axis=0))
    sums/=np.maximum(1e-12,np.linalg.norm(sums,axis=1)[:,None])
    smooth=sums[idx].reshape(-1,3,3)
    n[affected]=np.where(moved[face][:,:,None],smooth,n[affected])
    d["normals"]=n.tolist()
    d["positions"]=p.tolist()
    return d


def main():
    studio.setup("01_KevlarVest.blend")
    bpy.context.preferences.filepaths.save_version=0
    for rig in ("Kaitlin","Jason"):
        garment=patch_part(rig,"shirt_detail","cloth")
        gear=patch_part(rig,"vest","carrier")
        merge(garment,gear)
        studio.author(garment,"TS01_Vest_"+rig)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob,do_unlink=True)
    ob=studio.ns["mesh"](garment,"GAME_TS01_Vest")
    studio.iconns["bones"]=garment["bones"]
    icon=studio.iconns["icon"](ob,"ue_modern_kevlar_vest",3,3,"vest")
    display=studio.read(icon["display"])
    display["materials"]=[next(path for path in garment["materials"]
                               if studio.material(path).name.split(".")[0]==name)
                          for name in display["material_slots"]]
    studio.write(icon["display"],display)
    p=np.asarray(garment["positions"])
    garment["positions"]=(p-(p.min(0)+p.max(0))*.5).tolist()
    pickup=OUT/"vest-pickup.json"
    studio.write(pickup,garment)
    (OUT/"artwork.json").write_text(json.dumps(dict(icon=icon,pickup=str(pickup)),indent=2))


if __name__=="__main__":
    main()
