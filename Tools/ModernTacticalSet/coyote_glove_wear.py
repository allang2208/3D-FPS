"""Resolve the live TS01 wearing routes and their native binding donors."""
import hashlib
import json
import os
from pathlib import Path

P = Path(__file__).resolve().parents[2]
REV = "CoyoteGlovesR2"
BASE = "/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113"
DEST = BASE + "/" + REV
ROOT = P / "SourceAssets/ModernTacticalSet20261113" / REV
WEAR = ROOT / "Wear"
CONFIG = P / "Content/ColdSteelData/modular_outfits.json"
KEY = "ue_modern_tactical_gloves"
SLOTS = ("CG_Knit","CG_Suede","CG_Stretch","CG_Rubber","CG_Webbing","CG_Thread","CG_Label")
BRANCH = {"Jason":(), "Kaitlin":("body_variants","kaitlin")}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open("rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".writing")
    temp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    os.replace(temp,path)


def package_path(asset):
    if not asset.startswith("/Game/"):
        raise ValueError(asset)
    return P/"Content"/(asset[6:].split(".")[0]+".uasset")


def branch(config,body):
    for k in BRANCH[body]:
        config=config[k]
    return config


def plan():
    path=WEAR/"plan.json"
    if path.is_file():
        return read(path)
    config=read(CONFIG)
    inputs={}
    roles={}
    for body in BRANCH:
        section=branch(config,body)
        bindings=section["items"][KEY]["rig_meshes"]
        for rig,previous in bindings.items():
            name=f"SK_TS01_CoyoteGloves_{rig}"
            target=f"{DEST}/Wear/{rig}/{name}.{name}"
            if not previous.startswith(BASE+"/") or previous==target:
                raise RuntimeError(f"Missing previous native binding for {body}/{rig}")
            row=inputs.setdefault(rig,dict(previous=previous,asset=target))
            if row["previous"]!=previous:
                raise RuntimeError(f"Distinct binding for shared profile {rig} on {body}")
        roles[body]=dict(routes=dict(bindings), profiles={name:p["rig_profile"] for name,p in section["profiles"].items()})
        unmapped=set(roles[body]["profiles"].values())-bindings.keys()
        if unmapped:
            raise RuntimeError(f"{body} glove profiles lack native bindings: {unmapped}")
    for row in inputs.values():
        row["donor_package_sha256"]=sha(package_path(row["previous"]))
    result=dict(revision=REV,rigs=inputs,body_routes=roles)
    write(path,result)
    return result


if __name__=="__main__":
    data=plan()
    print("GLOVE_WEAR_ROUTES",len(data["rigs"]),{k:(len(b["routes"]),len(b["profiles"])) for k,b in data["body_routes"].items()})
