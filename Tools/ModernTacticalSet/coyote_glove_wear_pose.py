"""Track the saved near-surface glove skin against the original moving native hand."""
import gzip
import json

import numpy as np
from scipy.spatial import cKDTree

from coyote_glove_wear import ROOT,WEAR,read,sha,write
from native_glove_review import Skin,component


def unpack(path):
    with gzip.open(path,"rt",encoding="utf8") as stream:
        return json.load(stream)


def run():
    saved=read(ROOT/"wear-saved.json")
    prior=ROOT.parent/"NativeGloveR1"
    result={}
    for rig,folder,labels in (("Super90",prior,("M870","Super90")),("M16",prior/"M16",("M16",))):
        mesh=unpack(WEAR/f"{rig}-saved-hand.json.gz")
        for label in labels:
            poses=unpack(folder/"Read"/f"{label}_poses.json.gz")
            ids={name:i for i,name in enumerate(poses["names"])}
            parents=[ids.get(n,-1) for n in poses["parents"]]
            glove=Skin(mesh,poses["names"],True)
            native=Skin(read(folder/"Read"/f"{label}_Jason.json"),poses["names"],True)
            if glove.region.keys()!=native.region.keys():
                raise RuntimeError(f"Wrong native finger groups for {label}: {glove.region.keys()}")
            clips={}
            for name,clip in poses["clips"].items():
                stats=[]
                for local in clip["local"]:
                    pose=component(local,parents)
                    wearing=glove.skin(pose)
                    bare=native.skin(pose)
                    distances=[cKDTree(bare[ix]).query(wearing[glove.region[digit]])[0] for digit,ix in native.region.items()]
                    stats.append(float(np.percentile(np.concatenate(distances),95)))
                clips[name]=dict(samples=len(stats),worst_frame_p95_mm=round(10*max(stats),3))
            result[label]=dict(skeletal_package_sha256=saved["rigs"][rig]["package_sha256"],rig=rig,
                               captured_glove_source_sha256=sha(WEAR/f"{rig}-saved-hand.json.gz"),
                               samples=sum(c["samples"] for c in clips.values()),clips=clips,
                               worst_frame_p95_mm=max(c["worst_frame_p95_mm"] for c in clips.values()))
            print("COYOTE_GLOVE_NATIVE_ACTION_FRAMES",label,len(clips),result[label]["samples"],result[label]["worst_frame_p95_mm"],flush=True)
    write(WEAR/"posed-attachments.json",dict(results=result,gameplay_tested=False,
          measurement="Saved LOD0 source-model weights and positions on the knit, stretch and suede surfaces, sampled against the closest native point on the same digit and side; millimetres. Native saved animation transforms as captured in NativeGloveR1."))


if __name__=="__main__":
    run()
