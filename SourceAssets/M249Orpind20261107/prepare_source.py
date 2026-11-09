"""Produce editable M249 mesh groups from build 2 and keep the source texture atlas."""
from collections import defaultdict
import io
import json
import zipfile
from PIL import Image
import numpy as np
from source_geometry import ROOT, read_primitives
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

def group(mi,k):
    if mi==2: return "MagnifierGlass"
    if mi==1: return "Magnifier"
    if k in (64,71):return "HoloGlass"
    if k in (67,68):return "HoloReticle"
    if k in (84,85):return "MagnifierGlass"
    if k==78:return "MagnifierYoke"
    if k>=124: return "Stock"
    if k==0: return "Muzzle"
    if k==12: return "LegRight"
    if k==13: return "LegLeft"
    if 14<=k<=19 or k==11: return "BipodMount"
    if k in (1,2,3,4,5,6,7,8,9,10,20,25): return "Barrel"
    if k in (26,27,29,31,33,34,35,36,39,40,41,42): return "Handguard"
    if k in (28,30,32): return "Foregrip"
    if k in (37,38,44): return "Carry"
    if k in (51,52,53,55): return "Box"
    if k==46: return "Handle"
    if k in (47,48,49,54,60,61,62,65,69,72,73,75,82,89): return "Cover"
    if k in (56,57,58,59,63,64,66,67,68,70,71,74): return "Optic"
    if 76<=k<=122 and k not in (88,89,102,114): return "Magnifier"
    if k==50: return "Tray"
    return "Receiver"

def prepare():
    out=ROOT/"Geometry"
    out.mkdir(exist_ok=True)
    parts=defaultdict(list)
    for mi,pos,norm,uv,triangles,labels in read_primitives():
        if mi>2:continue
        for k in np.unique(labels):
            f=triangles[labels==k]
            pieces={group(mi,int(k)):f}
            if mi==0 and k==21:
                centre=pos[f].mean(axis=1)*100
                lower=(centre[:,0]>3.6)&(centre[:,0]<23)&(centre[:,2]<-4.2)
                _,weld=np.unique(np.rint(pos*1e6).astype(int),axis=0,return_inverse=True)
                corners=weld[f[lower]]
                graph=coo_matrix((np.ones(corners.size),(corners.ravel(),np.roll(corners,1,axis=1).ravel())),shape=(weld.max()+1,)*2)
                _,component=connected_components(graph,directed=False)
                tip=np.argmin(np.linalg.norm(centre[lower]-[8.8,.2,-6.1],axis=1))
                mask=np.zeros(len(f),dtype=bool)
                mask[lower]=component[corners[:,0]]==component[corners[tip,0]]
                grip=(centre[:,0]>12.7)&(centre[:,2]<-6.3)&~mask
                pieces={"Trigger":f[mask],"RearGrip":f[grip],"Receiver":f[~(mask|grip)]}
            for part,faces in pieces.items():
                ids,indices=np.unique(faces,return_inverse=True)
                parts[part].append((pos[ids],norm[ids],uv[ids],indices.reshape(-1,3)))
    for name,pieces in parts.items():
        shifted=[]; count=0
        for vertices,_,_,faces in pieces:
            shifted.append(faces+count)
            count+=len(vertices)
        p,n,uv=[np.concatenate([piece[i] for piece in pieces]) for i in range(3)]
        np.savez_compressed(out/(name+".npz"),positions=p,normals=n,uv=uv,faces=np.vstack(shifted))
    tex=ROOT/"Textures"
    tex.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT/"Original/M249_gltf.zip") as z:
        for channel,original in {"Color":"1_baseColor.png","ORM":"1_metallicRoughness.png","Normal":"1_normal.png","Emission":"1_emissive.jpeg","Transmission":"2_transmission.png"}.items():
            entry="textures/m249_diy_2_"+original
            if channel=="Transmission":
                im=Image.open(io.BytesIO(z.read(entry))).convert("L")
                im.resize((1024,1024),Image.Resampling.LANCZOS).save(tex/"T_M249_Transmission.png")
            else:
                (tex/("T_M249_"+channel+"."+original.split(".")[-1])).write_bytes(z.read(entry))
        license_text=z.read("license.txt").decode()
        (ROOT/"Original/license.txt").write_text(license_text,encoding="utf8")
        notice=ROOT.parents[1]/"ThirdPartyNotices/M249_Orpind.md"
        notice.write_text(license_text+"\nGame adaptation: build 2 selected, external parts separated, viewmodel rig and fitted first-person animation added. The separate project arm and feed assets retain their original credits.\n",encoding="utf8")
if __name__=="__main__":prepare()
