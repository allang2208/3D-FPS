import json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
def head_json(rel):
    raw=subprocess.run(["git","show","HEAD:"+rel],capture_output=True,cwd="D:/FPS3D/FPSGAME").stdout
    return json.loads(raw.decode("utf-8"))
for rel in ("Content/ColdSteelData/items.json","Content/ColdSteelData/gunsmith.json",
            "Content/ColdSteelData/combat-weapon-formulas.json","Content/ColdSteelData/modular_outfits.json"):
    old=head_json(rel); new=json.loads(open("D:/FPS3D/FPSGAME/"+rel,encoding="utf-8").read())
    if isinstance(old,dict) and "weapons" in old:
        oldk={w["id"]:w for w in old["weapons"]}; newk={w["id"]:w for w in new["weapons"]}
    elif isinstance(old,dict):
        oldk,newk=old,new
    print(rel)
    print("  added:", sorted(set(newk)-set(oldk)))
    print("  removed:", sorted(set(oldk)-set(newk)))
    changed=[k for k in set(oldk)&set(newk) if oldk[k]!=newk[k]]
    print("  modified:", changed)
