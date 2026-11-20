"""Resolve the current TS01 first-person sleeves and their native tailoring sources."""
from pathlib import Path

from coyote_glove_wear import BASE, BRANCH, CONFIG, P, branch, package_path, read, sha, write


KEY = "ue_modern_kevlar_vest"
REV = "PatrolShirtR2"
SET = P / "SourceAssets/ModernTacticalSet20261113"
ROOT = SET / REV
OUT = ROOT / "Sleeves"
DEST = BASE + "/" + REV
SLOTS = ["PS_" + name for name in ("Ripstop", "Binding", "Jersey", "Thread", "Reinforcement", "Loop", "Hardware")]


def plan():
    output = OUT / "plan.json"
    if output.is_file():
        return read(output)
    cfg = read(CONFIG)
    previous = SET / "CombatShirtR4"
    authored = {v["asset"]:v for v in read(previous/"authored.json")["rows"] if "shirt_fp_" in v["file"]}
    source_receipts = read(previous/"saved.json")["wear"]
    installed = {Path(v["path"]):v["sha256"] for v in read(previous/"installed.json")["packages"]}
    rigs, bodies = {}, {}
    for body in BRANCH:
        section = branch(cfg,body)
        shirt = section["items"][KEY]
        routes = {k:v for k,v in shirt["rig_meshes"].items() if k not in BRANCH}
        for rig,path in routes.items():
            package = path.split(".")[0]
            row = authored[package]
            source = Path(row["file"])
            package_hash = sha(package_path(path))
            if package_hash != installed[package_path(path)] or sha(source)!=source_receipts[package]["sha256"]:
                raise RuntimeError("Regenerate the authored sleeve from the changed donor "+path)
            name = "SK_TS01_PatrolSleeves_" + rig
            new = DEST + "/Sleeves/"+rig+"/"+name+"."+name
            entry = dict(rig=rig,previous=path,asset=new,donor_sha256=package_hash,
                         source=source.relative_to(SET).as_posix(),source_sha256=source_receipts[package]["sha256"],
                         authored="Sleeves/Authored/"+rig+".json.gz")
            if rigs.setdefault(rig,entry)!=entry:
                raise ValueError("Distinct native bindings share the same rig name "+rig)
        bodies[body] = dict(routes=routes,body_materials=shirt.get("base_material_overrides",{}).get("Body",{}),
                            bare_wrists=shirt["bare_wrist_materials"],
                            pose_profiles={k:v["rig_profile"] for k,v in section["profiles"].items() if v["rig_profile"] in routes})
    result = dict(rigs=rigs,bodies=bodies)
    write(output,result)
    return result


if __name__=="__main__":
    print("Patrol shirt native sleeve bindings",len(plan()["rigs"]))
