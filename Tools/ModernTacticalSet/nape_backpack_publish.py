"""Install the saved TS01 pack recesses without changing other equipment pairs."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

import numpy as np

P=Path(__file__).resolve().parents[2]
S=P/"SourceAssets/ModernTacticalSet20261113"
R=P/"SourceAssets/BackpackFit20261024/ModernTacticalHelmetPacks20261118"
OLD=R.with_name("ModernTacticalShoulders20261118")
TOOLS=P/"Tools/BackpackFit"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def write(name,data):
    (R/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")


def obj(asset):
    return asset if "." in asset else asset+"."+asset.rsplit("/",1)[-1]


def publish():
    rigpack=read(OLD/"published.json")
    if rigpack.get("status")!="saved_and_integrated":
        raise RuntimeError("The shoulder fit is not published")
    for rig,digest in read(R/"helmet-sha256.json").items():
        if sha(S/"HelmetNapeR3/Authored"/f"helmet_{rig}_world.json")!=digest:
            raise RuntimeError("Helmet surface changed during pack fitting")
    rows=read(R/"routes.json");sources=read(R/"authored.json");saved=read(R/"saved_assets.json")
    if not saved.get("completed"):
        raise RuntimeError("Pack assets still being written")
    hashes={}
    for kind,assets in (("meshes",sources["rows"]),("statics",sources["statics"])):
        for entry in assets:
            asset=entry["asset"]
            if saved[kind][asset]["geometry_sha256"]!=sha(Path(entry["positions"])):
                raise RuntimeError(f"Geometry mismatch for {asset}")
            hashes[asset]=sha(P/"Content"/(asset.removeprefix("/Game/")+".uasset"))
    oldfits={(q["rig"],q["item"]):q for q in read(OLD/"authored.json")["rows"]}
    records=read(OLD/"captured.json")
    sk={q["asset"]:q for q in sources["rows"]}
    path=P/"Content/ColdSteelData/player_body.json";raw=path.read_bytes();cfg=json.loads(raw);owned=[]
    for q in rows:
        rig,item,shirt=q["rig"],q["item"],q["shirt"]
        root=(() if rig=="Jason" else ("body_variants","kaitlin"))+("outfits",item)
        outfit=cfg
        for k in root:outfit=outfit[k]
        def assign(node,suffix,leaf,expected,value):
            if node[leaf]!=expected and node[leaf]!=value:
                raise RuntimeError(f"Concurrent outfit edit: {rig}/{item}/{suffix}/{leaf}")
            node[leaf]=value;owned.append(root+suffix+(leaf,))
        old=oldfits[rig,item]
        if q.get("mesh"):
            assign(outfit["world_mesh_by_shirt"],("world_mesh_by_shirt",),shirt,obj(q["expected_mesh"]),obj(q["mesh"]))
        elif outfit["world_mesh_by_shirt"][shirt]!=obj(q["expected_mesh"]):
            raise RuntimeError("The fitted harness changed: "+item)
        if q.get("rigid"):
            motion=outfit["rigid_pack"]
            if motion["location_by_shirt"][shirt]!=old["rigid_location"] or motion["rotation_quat"]!=old["rigid_rotation_quat"]:
                raise RuntimeError("The pack transform changed: "+item)
            assign(motion["mesh_by_shirt"],("rigid_pack","mesh_by_shirt"),shirt,q["expected_rigid"],obj(q["rigid"]))
        elif q.get("mesh") and q.get("before_support"):
            record=sk[q["mesh"]];donor=records[record["source"]]
            points=np.fromfile(record["positions"],dtype="<f4").reshape(-1,3)
            f=np.fromfile(Path(donor["folder"])/"triangles.bin",dtype="<i4").reshape(-1,3)
            cargo=np.fromfile(donor["cargo_vertices"],dtype="u1")
            upper=points[np.unique(f[np.all(cargo[f]>0,axis=1)])]
            q["after_support"]={**q["before_support"],"bounds_min":upper.min(0).tolist(),"bounds_max":upper.max(0).tolist()}
        motion=outfit["backpack_motion"]
        if q.get("after_support"):
            assign(motion["support_by_shirt"],("backpack_motion","support_by_shirt"),shirt,q["before_support"],q["after_support"])
        for field,combine in (("bounds_min",min),("bounds_max",max)):
            oldbound=motion[field]
            value=[combine(a,b) for a,b in zip(oldbound,q[field])]
            if oldbound!=value:
                motion[field]=value;owned.append(root+("backpack_motion",field))
    receipt=runpy.run_path(str(P/"Tools/PlayerBody/config_transaction.py"))["commit"](path,raw,cfg,owned_paths=owned,producer=__file__)
    write("config-receipt.json",receipt)

    # Regenerate fingerprints for just these seven live routes; a compare-and-swap
    # preserves other clothing authors' registry entries if they advance.
    os.environ["BACKPACK_FIT_RUN_DIR"]=str(R);sys.path.insert(0,str(TOOLS))
    from pending import signatures,REG
    runpy.run_path(str(TOOLS/"prepare.py"),run_name="__main__")
    plan=read(R/"plan.json")
    selected={(q["rig"],q["item"],q["shirt"]) for q in rows}
    plan["rows"]=[q for q in plan["rows"] if (q["rig"],q["item"],q["shirt"]) in selected]
    updates=signatures(plan)
    if len(updates)!=len(rows):
        raise RuntimeError("Live coverage no longer matches the produced pairs")
    for _ in range(3):
        before=REG.read_bytes();registry=json.loads(before);registry["routes"].update(updates);registry["revision"]=R.name
        with tempfile.NamedTemporaryFile(dir=REG.parent,delete=False) as f:
            f.write((json.dumps(registry,ensure_ascii=False,indent=2)+"\n").encode("utf8"))
        tmp=Path(f.name)
        try:
            if REG.read_bytes()!=before:continue
            os.replace(tmp,REG);break
        finally:tmp.unlink(missing_ok=True)
    else:raise RuntimeError("Registry advanced during merge")
    write("published.json",dict(status="saved_and_integrated",revision=R.name,pack_combinations=len(rows),changed_harness_or_soft=len(sk),
                                changed_rigid=len(sources["statics"]),packages_sha256=hashes,registered_routes=sorted(updates),runtime_tested=False))
    print("NAPE_PACKS_PUBLISHED",len(rows),len(hashes),flush=True)


if __name__=="__main__":
    publish()
