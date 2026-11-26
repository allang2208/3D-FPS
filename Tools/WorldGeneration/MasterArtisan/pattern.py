"""Common paths and skinned geometry for the mechanical workshop resident (UE centimetres)."""
from pathlib import Path
import gzip
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "SourceAssets/HillsVillageHighWall20261120/MasterArtisan"
SMITH = ROOT / "SourceAssets/VillageBlacksmithNPC20261118"
STRONG = ROOT / "SourceAssets/JasonStrong20261117"

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def normalized(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-10)

class Piece:
    def __init__(self):
        self.p, self.n, self.uv, self.w, self.tri, self.m = [], [], [], [], [], []
        self.index = {}

    def corner(self, pos, norm, uv, weights):
        key = (*pos, *norm, *uv, *(tuple(pair) for pair in weights))
        if key not in self.index:
            self.index[key] = len(self.p)
            self.p.append(np.round(pos,5).tolist())
            self.n.append(np.round(norm,5).tolist())
            self.uv.append(np.round(uv,6).tolist())
            self.w.append(weights)
        return self.index[key]

    def face(self, ids, mat):
        self.tri.append(list(ids))
        self.m.append(mat)

    def grid(self, positions, weights, mat, uvscale=(1,1), reverse=False, radial=False):
        p=np.array(positions)
        h,w=p.shape[:2]
        n=normalized(np.cross(np.gradient(p,axis=0),np.gradient(p,axis=1)))
        if radial:
            n=normalized(p-np.mean(p,axis=1,keepdims=True))
        if reverse and not radial:
            n=-n
        ids=[[self.corner(p[j,i],n[j,i],[uvscale[0]*i/(w-1),uvscale[1]*j/(h-1)],weights(p[j,i])) for i in range(w)] for j in range(h)]
        for j in range(h-1):
            for i in range(w-1):
                a,b,c,d=ids[j][i],ids[j][i+1],ids[j+1][i+1],ids[j+1][i]
                for tri in [(a,b,c),(a,c,d)]:
                    pp=np.array([self.p[k] for k in tri])
                    if np.dot(np.cross(pp[2]-pp[0],pp[1]-pp[0]),n[j,i])<0:
                        tri=tri[::-1]
                    self.face(tri, mat)

    def tube(self, path, radius, mat, weights, sides=10):
        path=np.array(path)
        tangent=normalized(np.gradient(path,axis=0))
        ref=np.eye(3)[np.argmin(np.abs(tangent).mean(0))]
        a=normalized(np.cross(tangent,ref))
        b=normalized(np.cross(tangent,a))
        angle=np.linspace(0,2*np.pi,sides+1)
        rings=path[:,None,:]+radius*(a[:,None,:]*np.cos(angle)[None,:,None]+b[:,None,:]*np.sin(angle)[None,:,None])
        self.grid(rings,weights,mat,radial=True)

    def save(self, name, materials, folder=SRC):
        with gzip.open(folder/(name+".json.gz"),"wt",encoding="utf8",compresslevel=4) as f:
            json.dump({key:getattr(self,key) for key in ("p","n","uv","w","tri","m")} | {"materials":materials},f,separators=(",",":"))
