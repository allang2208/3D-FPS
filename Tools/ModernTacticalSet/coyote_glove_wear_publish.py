"""Switch both glove recipes after every listed native rig is present on disk."""
import json
import os
from pathlib import Path
import sys
import tempfile

from coyote_glove_wear import BRANCH,CONFIG,KEY,P,ROOT,branch,package_path,plan,read,sha,write

sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import span


def main():
    work=plan()
    meshes=read(ROOT/"wear-saved.json")
    if not meshes["complete"] or meshes["rigs"].keys()!=work["rigs"].keys():
        raise RuntimeError("All active native glove variants must be saved before rollout")
    policy=meshes["policy"]
    if sha(package_path(policy["asset"]))!=policy["sha256"]:
        raise RuntimeError("Glove distance LOD policy differs from the saved revision")
    for key,row in meshes["rigs"].items():
        if (sha(ROOT/row["source_file"])!=row["source_sha256"] or
            sha(package_path(row["asset"]))!=row["package_sha256"] or
            row["asset"]!=work["rigs"][key]["asset"]):
            raise RuntimeError(f"Saved glove and source disagree for {key}")
    for attempt in range(4):
        before=CONFIG.read_bytes()
        doc=json.loads(before)
        original=before.decode("utf-8-sig")
        edits=[]
        scoped={}
        for body in BRANCH:
            section=branch(doc,body)
            profiles={name:p["rig_profile"] for name,p in section["profiles"].items()}
            recipe=section["items"][KEY]
            routes=recipe["rig_meshes"]
            if routes.keys()!=work["body_routes"][body]["routes"].keys() or set(profiles.values())-routes.keys():
                raise RuntimeError("The active set of glove bindings changed during production on "+body)
            if recipe.get("owner_body_meshes") or recipe.get("skin_meshes") or recipe.get("material"):
                raise RuntimeError("Unexpected independent glove layer override on "+body)
            scoped[body]={"routes":{},"pose_profiles":profiles}
            for rig,old in routes.items():
                new=meshes["rigs"][rig]["asset"]
                if old not in (work["rigs"][rig]["previous"],new):
                    raise RuntimeError(f"Concurrent change to {body}/{rig} at {old}")
                scoped[body]["routes"][rig]=new
                if old!=new:
                    fields=(*BRANCH[body],"items",KEY,"rig_meshes",rig)
                    start,end=span(original,fields)
                    edits.append((start,end,json.dumps(new)))
        chunks=[]
        pos=0
        for start,end,value in sorted(edits):
            chunks.extend((original[pos:start],value));pos=end
        chunks.append(original[pos:])
        updated="".join(chunks)
        payload=(b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"")+updated.encode("utf-8")
        if payload!=before:
            with tempfile.NamedTemporaryFile(dir=CONFIG.parent,delete=False) as tmp:
                tmp.write(payload)
                temp=Path(tmp.name)
            try:
                if CONFIG.read_bytes()!=before:
                    continue
                os.replace(temp,CONFIG)
            finally:
                temp.unlink(missing_ok=True)
        else:
            if CONFIG.read_bytes()!=before:
                continue
        write(ROOT/"wear-published.json",dict(rigs=meshes["rigs"],body_routes=scoped,policy=policy,
               config="Content/ColdSteelData/modular_outfits.json",gameplay_tested=False))
        print("COYOTE_GLOVE_WEAR_PUBLISHED",len(meshes["rigs"]),sum(len(v["routes"]) for v in scoped.values()))
        return
    raise RuntimeError("The shared outfit configuration kept changing during publication")


if __name__=="__main__":
    main()
