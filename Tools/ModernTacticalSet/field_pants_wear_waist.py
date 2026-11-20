"""Sample the native waist contact surface before reusing the saved upper-body fits."""
import math
import numpy as np

from field_pants_wear import ROOT, SET, plan, read, sha, write


def load_shell(data):
    slots=data["material_slots"]
    fabric=[i for i,k in enumerate(slots) if k in ("TS01_RangerRipstop","TS01_CharcoalStretch","FT_Ripstop","FT_Stretch")]
    faces=np.asarray(data["triangles"],int)[np.isin(data["triangle_materials"],fabric)]
    positions=np.asarray(data["positions"])
    top=positions[faces,2].max()
    faces=faces[positions[faces,2].max(1)>top-10.]
    return positions[faces],faces,data["weights"],{b["index"]:b["name"] for b in data["bones"]},top


def sample(shell,angle,z):
    points,faces,weights,bones,_=shell
    radial=np.array([math.cos(angle),math.sin(angle)])
    lateral=np.array([-radial[1],radial[0]])
    xy=points[:,:,:2]-[0.,.8]
    p=np.stack((xy@lateral,points[:,:,2]-z),axis=-1)
    # Barycentric coordinates of the ray within each triangle's profile
    # on the plane perpendicular to that ray.
    def det(a,b):
        return a[:,0]*b[:,1]-a[:,1]*b[:,0]
    area=det(p[:,1]-p[:,0],p[:,2]-p[:,0])
    eligible=np.flatnonzero(np.abs(area)>1.e-7)
    q=p[eligible]
    co=np.stack((det(q[:,1],q[:,2]),det(q[:,2],q[:,0]),det(q[:,0],q[:,1])),axis=1)/area[eligible,None]
    r=np.sum((xy[eligible]@radial)*co,axis=1)
    hits=np.flatnonzero((co.min(1)>=-1.e-7)&(r>2.))
    if not len(hits):
        return None
    i=hits[np.argmin(r[hits])]
    skin={}
    for vertex,coefficient in zip(faces[eligible[i]],co[i]):
        for bone,weight in weights[vertex]:
            name=bones[bone]
            skin[name]=skin.get(name,0.)+coefficient*weight
    return float(r[i]),skin


def waist(row):
    old_file=SET/row["donor_source"]
    new_file=ROOT/row["source"]
    old=load_shell(read(old_file))
    new=load_shell(read(new_file))
    errors=[]
    influences=[]
    lost=0
    for angle in np.linspace(0.,math.tau,32,endpoint=False):
        for z in old[4]-np.array([1.,2.5,4.,5.5,7.]):
            prior=sample(old,angle,z)
            if not prior:
                continue
            current=sample(new,angle,z)
            if not current:
                lost+=1
                continue
            errors.append(abs(prior[0]-current[0])*10.)
            influences.append(max(abs(prior[1].get(b,0.)-current[1].get(b,0.)) for b in prior[1].keys()|current[1].keys()))
    if not errors:
        raise ValueError("No fitted fabric rings present on "+new_file.name)
    return dict(donor_source_sha256=sha(old_file),source_sha256=sha(new_file),samples=len(errors),missing=lost,
                peak_offset_mm=round(max(errors),4),p95_offset_mm=round(float(np.percentile(errors,95)),4),
                peak_influence_delta=round(max(influences),6))


def main():
    target=ROOT/"Wear/waist-interfaces.json"
    entries=read(target)["assets"] if target.exists() else {}
    for name,row in plan()["assets"].items():
        source=ROOT/row["source"]
        if source.is_file() and entries.get(name,{}).get("source_sha256")!=sha(source):
            entries[name]=waist(row)
            print(name,entries[name]["samples"],entries[name]["missing"],entries[name]["peak_offset_mm"],entries[name]["peak_influence_delta"],flush=True)
            write(target,dict(assets=entries,method="Innermost ripstop/stretch surface radius and barycentric native bone weights at 32 angles and 5 heights through the top 7 cm of the original trousers."))


if __name__=="__main__":
    main()
