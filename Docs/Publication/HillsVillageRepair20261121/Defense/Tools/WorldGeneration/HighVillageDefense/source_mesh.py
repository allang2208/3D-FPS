"""Prepare the actual multiview surfaces in the village's X-span, Z-up centimetre basis."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import cv2
import numpy as np
import trimesh
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "SourceAssets/HillsVillageHighWall20261120/Design01"
OUT = SOURCE / "Authored"


class Surface:
    def __init__(self, pos, faces, uv):
        self.pos = np.asarray(pos, dtype=np.float64)
        self.faces = np.asarray(faces, dtype=np.int32)
        self.uv = np.asarray(uv, dtype=np.float64)

    def moved(self, pos, flip=False):
        return Surface(pos, self.faces[:, ::-1] if flip else self.faces, self.uv)

    def clipped(self, distance):
        """Keep the positive half-space and interpolate the GLB UVs on new cut edges."""
        signed = np.asarray(distance(self.pos))
        sides = signed[self.faces]
        intact = list(self.faces[np.all(sides >= 0, axis=1)])
        cut = self.faces[np.logical_and(sides.min(axis=1)<0, sides.max(axis=1)>=0)]
        pos, uv, intersections = [], [], {}
        for face in cut:
            poly=[]
            for a,b in zip(face,np.roll(face,-1)):
                if signed[a]>=0:
                    poly.append(a)
                if (signed[a]>=0) == (signed[b]>=0):
                    continue
                key=(min(a,b),max(a,b))
                index=intersections.get(key)
                if index is None:
                    index=len(self.pos)+len(pos)
                    t=signed[a]/(signed[a]-signed[b])
                    pos.append(self.pos[a]+t*(self.pos[b]-self.pos[a]))
                    uv.append(self.uv[a]+t*(self.uv[b]-self.uv[a]))
                    intersections[key]=index
                poly.append(index)
            for i in range(1,len(poly)-1):
                intact.append((poly[0],poly[i],poly[i+1]))
        if not intact:
            return None
        p=np.vstack([self.pos,pos]) if pos else self.pos
        coords=np.vstack([self.uv,uv]) if uv else self.uv
        used,ids=np.unique(np.asarray(intact).ravel(),return_inverse=True)
        return Surface(p[used],ids.reshape(-1,3),coords[used])


def put_maps(role, material, index):
    """Meshy embeds glTF metallic/roughness channels. Use the chapel PBR master."""
    slot=role if index==0 else f"{role}{index+1}"
    target=OUT/"Textures";target.mkdir(parents=True,exist_ok=True)
    base=material.baseColorTexture
    normal=material.normalTexture
    if base is None or normal is None:
        raise RuntimeError(f"{role} is missing its generated base color or tangent normal")
    base.convert("RGB").save(target/f"{slot}_base_color.png")
    normal.convert("RGB").save(target/f"{slot}_normal.png")
    mr=material.metallicRoughnessTexture
    if mr is None:
        rough=Image.new("L",(4,4),round(255*float(material.roughnessFactor if material.roughnessFactor is not None else .8)))
        metal=Image.new("L",(4,4),round(255*float(material.metallicFactor if material.metallicFactor is not None else 0.)))
    else:
        rgb=mr.convert("RGB")
        rough=rgb.getchannel("G");metal=rgb.getchannel("B")
    rough.save(target/f"{slot}_roughness.png");metal.save(target/f"{slot}_metallic.png")
    return slot


def read_source(folder, role):
    original=SOURCE/"Meshy"/folder/"model.glb"
    digest=hashlib.sha256(original.read_bytes()).hexdigest()[:12]
    cache=Path(os.environ.get("HIGH_VILLAGE_CACHE","F:/FPSGAMEData/Caches/Authoring/HighVillageDefense/Reduced"))
    budget={"A_HighWall":65000,"B_WestArch":50000,"C_WestGrille":75000}[folder]
    source=cache/f"{folder}-{digest}-{budget}.glb"
    scene=trimesh.load(source,force="scene",process=False)
    parts=[]; mats={}
    for node in scene.graph.nodes_geometry:
        transform,key=scene.graph[node]
        mesh=scene.geometry[key].copy()
        mesh.apply_transform(transform)
        if not len(mesh.faces):continue
        material=mesh.visual.material
        key=hash(material)
        if key not in mats:mats[key]=put_maps(role,material,len(mats))
        raw=np.asarray(mesh.vertices)
        pos=np.stack((raw[:,0],-raw[:,2],raw[:,1]),axis=1)
        uv=np.array(mesh.visual.uv);uv[:,1]=1.-uv[:,1]
        parts.append((mats[key],Surface(pos,mesh.faces,uv)))
    all_pos=np.vstack([p.pos for _,p in parts])
    # Align the broad face of the generated object even if its authored yaw is oblique.
    _,axes=np.linalg.eigh(np.cov(all_pos[:,:2].T))
    x=axes[:,-1]
    if x[0]<0:x=-x
    basis=np.column_stack((x,[-x[1],x[0]]))
    mapped=all_pos.copy();mapped[:,:2]=mapped[:,:2]@basis
    lo,hi=mapped.min(axis=0),mapped.max(axis=0)
    size=hi-lo
    if min(size)<=0:raise ValueError("Degenerate source "+str(source))
    top=mapped[mapped[:,2]>lo[2]+size[2]*.89]
    swap=role=="HighWallStone" and np.mean(top[:,1])>(hi[1]+lo[1])*.5
    for _,p in parts:
        p.pos[:,:2]=p.pos[:,:2]@basis
        p.pos=(p.pos-lo)/size
        if swap:p.pos[:,:2]=1.-p.pos[:,:2]
    return parts


def silhouette(parts, resolution=512):
    """Derive the real aperture and rail positions from the received geometry."""
    mask=np.zeros((resolution,resolution),np.uint8)
    for _,part in parts:
        points=np.round(part.pos[:,[0,2]]*(resolution-1)).astype(np.int32)
        for tri in points[part.faces]:
            cv2.fillConvexPoly(mask,tri,255)
    return mask


def save_role(role,groups,construction):
    """Keep the compact indexed data separate from Unreal's Python runtime."""
    for slot,g in construction.groups.items():
        if not g["triangles"]:continue
        # Existing wall authoring already emits UE winding and outward normals.
        groups.setdefault(slot,[]).append((np.array(g["vertices"]),np.array(g["triangles"]),
            np.array(g["uv0"]),np.array(g["normals"])))
    result={"role":role,"materials":[],"boxes":construction.boxes,"faces":0}
    target=OUT/(role+".meshzip")
    with ZipFile(target.with_suffix(".partial"),"w",ZIP_DEFLATED,compresslevel=3) as archive:
        for slot,entries in groups.items():
            if not entries:continue
            idx=len(result["materials"]);result["materials"].append(slot)
            p,f,uv,n=[],[],[],[];offset=0
            for entry in entries:
                if isinstance(entry,Surface):
                    pos=entry.pos;faces=entry.faces;coord=entry.uv
                    clean=trimesh.Trimesh(pos,faces,process=False)
                    valid=clean.nondegenerate_faces(height=.0001)
                    if not valid.all():clean.update_faces(valid)
                    normal=clean.vertex_normals
                    indices=np.asarray(clean.faces)[:,::-1]
                else:
                    pos,indices,coord,normal=entry
                p.append(pos);uv.append(coord);n.append(normal);f.append(indices+offset);offset+=len(pos)
            arrays=(("vertices",p,"<f4"),("indices",f,"<i4"),("uv",uv,"<f4"),("normals",n,"<f4"))
            for key,items,dtype in arrays:
                archive.writestr(f"{idx}/{key}",np.ascontiguousarray(np.concatenate(items),dtype=dtype).tobytes())
            result["faces"]+=sum(len(i) for i in f)
        archive.writestr("mesh.json",json.dumps(result))
    target.with_suffix(".partial").replace(target)
    print("AUTHORED",role,result["faces"],flush=True)
