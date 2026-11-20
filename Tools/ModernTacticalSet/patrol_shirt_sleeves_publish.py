"""Point both outfit recipes to the saved sleeves while preserving their wrist skin bindings."""
import json
from pathlib import Path
import sys

from patrol_shirt_sleeves import BRANCH, CONFIG, KEY, P, ROOT, branch, package_path, plan, read, sha, write
from shoulder_packages import write_revision

sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import span


def replace_leaves(text,edits):
    for left,right,value in sorted(edits,reverse=True):
        text = text[:left]+value+text[right:]
    return text


def publish():
    saved = read(ROOT/"sleeves-saved.json")
    work = plan()
    if not saved["complete"] or saved["assets"].keys() != work["rigs"].keys():
        raise RuntimeError("Missing native sleeve packages")
    surfaces = read(ROOT/"saved-surfaces.json")["materials"]
    new_body = {"0":surfaces["Ripstop"],"1":surfaces["Ripstop"],"3":surfaces["Jersey"]}
    for rig,row in saved["assets"].items():
        if row["asset"] != work["rigs"][rig]["asset"] or sha(package_path(row["asset"])) != row["package_sha256"]:
            raise RuntimeError("Sleeve package changed before publication: "+rig)
    for attempt in range(4):
        original = CONFIG.read_bytes()
        text = original.decode("utf-8-sig")
        config = json.loads(original)
        sections = []
        published = {}
        for body,location in BRANCH.items():
            item = branch(config,body)["items"][KEY]
            source = work["bodies"][body]
            routes = {k:v for k,v in item["rig_meshes"].items() if k not in BRANCH}
            if routes.keys()!=work["rigs"].keys():
                raise RuntimeError("The native viewmodel bindings changed on "+body)
            begin,end = span(text,[*location,"items",KEY])
            section = text[begin:end]
            edits = []
            def route(fields,actual,old,new):
                if actual not in (old,new):
                    raise RuntimeError("A concurrent edit changed "+str((body,*fields)))
                if actual!=new:
                    left,right = span(section,fields)
                    edits.append((left,right,json.dumps(new)))
            for rig,path in routes.items():
                route(["rig_meshes",rig],path,source["routes"][rig],saved["assets"][rig]["asset"])
            for slot,mat in new_body.items():
                route(["base_material_overrides","Body",slot],item["base_material_overrides"]["Body"][slot],
                      source["body_materials"][slot],mat)
            if edits:
                sections.append((begin,end,replace_leaves(section,edits)))
            published[body] = dict(routes={k:v["asset"] for k,v in saved["assets"].items()},
                                  base_body_materials=new_body,bare_wrist_sources=list(item["bare_wrist_materials"]))
        bom = original[:3] if original.startswith(b"\xef\xbb\xbf") else b""
        updated = bom + replace_leaves(text,sections).encode("utf8")
        try:
            if updated!=original:
                write_revision(CONFIG,original,updated)
            elif CONFIG.read_bytes()!=original:
                continue
        except RuntimeError:
            if CONFIG.read_bytes()!=original:
                continue
            raise
        write(ROOT/"sleeves-published.json",dict(bodies=published,policy=saved["policy"],
              packages={k:v["package_sha256"] for k,v in saved["assets"].items()},gameplay_tested=False))
        print("Published",len(saved["assets"]),"native patrol sleeves in both shirt recipes.")
        return
    raise RuntimeError("The outfit recipe changed while publishing patrol sleeves")


if __name__=="__main__":
    publish()
