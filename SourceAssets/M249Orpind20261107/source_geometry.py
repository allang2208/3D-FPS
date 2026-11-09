"""Read the selected Sketchfab mesh islands without welding UV seams in the output."""
from pathlib import Path
import json
import zipfile
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parent
def read_primitives():
    with zipfile.ZipFile(ROOT / "Original/M249_gltf.zip") as archive:
        scene = json.loads(archive.read("scene.gltf"))
        buf = archive.read("scene.bin")
    def read(index):
        a = scene["accessors"][index]
        v = scene["bufferViews"][a["bufferView"]]
        dt = np.dtype({5126:"<f4",5125:"<u4",5123:"<u2",5121:"u1"}[a["componentType"]])
        cols = {"SCALAR":1,"VEC3":3,"VEC2":2,"VEC4":4}[a["type"]]
        return np.ndarray((a["count"],cols), dt, buf, v.get("byteOffset",0)+a.get("byteOffset",0),
                          (v.get("byteStride",dt.itemsize*cols),dt.itemsize)).copy()
    for mi, mesh in enumerate(scene["meshes"]):
        p = mesh["primitives"][0]
        pos,norm,uv = [read(p["attributes"][n]) for n in ("POSITION","NORMAL","TEXCOORD_0")]
        faces=read(p["indices"]).reshape(-1,3).astype(int)
        _,inverse = np.unique(np.rint(pos*1e6).astype(int),axis=0,return_inverse=True)
        weld=inverse[faces]
        graph=coo_matrix((np.ones(weld.size),(weld.ravel(),np.roll(weld,1,axis=1).ravel())),shape=(inverse.max()+1,)*2)
        _,parts=connected_components(graph,directed=False)
        yield mi,pos,norm,uv,faces,parts[inverse][faces[:,0]]

if __name__=="__main__":
    for mi,pos,norm,uv,faces,label in read_primitives():
        print("MESH",mi)
        for key in np.unique(label):
            f=faces[label==key]
            xyz=pos[f].reshape(-1,3)*100
            if len(f)>180 or mi in (1,2,4):
                print("%3d %5d"% (key,len(f)), np.round(xyz.min(0),1), np.round(xyz.max(0),1))
