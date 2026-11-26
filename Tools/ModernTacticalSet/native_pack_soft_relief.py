"""Relieve remaining strap-cloth intersections at the measured stations only."""
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from native_pack_soft_seat import R, C, read, preserve_groups


def relieve():
    for family in ("Soft","Rigid"):
        sources=read(R/family/("sources.json" if family=="Soft" else "original-sources.json"))
        for asset,recipe in zip(read(R/family/"author.json")["rows"],sources):
            name=asset["asset"].rsplit("/",1)[-1]
            file=C/(name+".bin")
            receipt=C/(name+"-contacts.npz")
            if not receipt.exists():continue
            ids=np.load(receipt)["ids"]
            if not len(ids):continue
            p=np.fromfile(file,"<f4").reshape(-1,3).astype(float)
            initial=np.fromfile(asset["positions"],"<f4").reshape(-1,3)
            cap=Path(recipe.get("source_directory") or recipe["source_harness_directory"])
            mask=np.fromfile(cap/"mask.bin","<f4")
            native=np.fromfile(cap/"positions.bin","<f4").reshape(-1,3)
            faces=np.fromfile(cap/"triangles.bin","<i4").reshape(-1,3)
            keep=~np.fromfile(recipe["cargo_vertices"],"u1").astype(bool) if family=="Soft" else np.ones(len(mask),bool)
            # Contact at the waist and anterior carrier needs lateral relief.
            # The taper carries a measured station's shift into adjacent rings.
            delta=np.zeros_like(p)
            cy=0. if recipe["rig"]=="Jason" else 6.
            delta[:,:2]=p[:,:2]-[0.,cy]
            delta/=np.maximum(.01,np.linalg.norm(delta,axis=1)[:,None])
            # Near the female carrier shoulder the normal turns upward.
            # Moving laterally here would enter the sleeve while skirting its pad.
            if recipe["rig"]=="Kaitlin":
                above=np.clip((p[:,2]-120.)/7.,0.,1.)
                front=np.clip((p[:,1]-cy+1.)/5.,0.,1.)
                shoulder=np.column_stack((np.zeros(len(p)),front,1.-front))
                shoulder/=np.maximum(.01,np.linalg.norm(shoulder,axis=1)[:,None])
                delta=delta*(1.-above[:,None])+shoulder*above[:,None]
            radius=cKDTree(p[ids]).query(p)[0]
            amount=np.exp(-.5*(radius/3.)**2)*.75*keep*np.clip((.97-mask)/.25,0.,1.)
            target=p+delta*amount[:,None]
            final=preserve_groups(native,initial,target,faces,keep,mask)
            final[~keep]=initial[~keep]
            final.astype("<f4").tofile(file)


if __name__=="__main__":relieve()
