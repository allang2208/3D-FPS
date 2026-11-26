"""Check captured UE source/render triangles against the two R3 nape pose sweeps."""
from pathlib import Path
import sys
import json
import numpy as np
from mathutils import Quaternion
sys.path.insert(0,str(Path(__file__).parent))
from nape_backpack_author import OLD,OUT,read,shells,contacts

def main():
    lods=read(OUT/"lod-read.json")
    saved=read(OUT/"published.json")
    if set(lods)!=set(saved["packages_sha256"]):raise RuntimeError("Incomplete saved package readback")
    routes=read(OUT/"routes.json");old={(r["rig"],r["item"]):r for r in read(OLD/"authored.json")["rows"]}
    data={}
    for rig in ("Jason","Kaitlin"):
        poses=shells(rig);data[rig]={}
        for row in routes:
            if row["rig"]!=rig:continue
            key=row["item"];record={}
            for field in ("mesh","rigid"):
                if field not in row:continue
                coords=old[rig,key];packs=lods[row[field]]
                for lod,location in packs.items():
                    folder=Path(location["directory"])
                    p=np.fromfile(folder/"points.bin",dtype="<f4").reshape(-1,3)
                    f=np.fromfile(folder/"faces.bin",dtype="<i4").reshape(-1,3)
                    if field=="rigid":
                        x,y,z,w=coords["rigid_rotation_quat"]
                        p=p@np.asarray(Quaternion((w,x,y,z)).to_matrix()).T+coords["rigid_location"]
                    counts=contacts([(p,f)],poses)
                    record[lod]=counts
            data[rig][key]=record
            print(rig,key,{lod:max(a.values()) for lod,a in record.items()},flush=True)
    (OUT/"saved-lod-contact.json").write_text(json.dumps(dict(poses=["head pivot and distributed neck, same six angles"],rows=data),indent=2))
if __name__=="__main__":main()
