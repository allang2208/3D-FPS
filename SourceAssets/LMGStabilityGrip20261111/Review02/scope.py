"""Compare engine-read joint tracks to the approved per-weapon donors."""
from pathlib import Path
import sys
import json
import gzip
import hashlib
import numpy as np
from scipy.spatial.transform import Rotation

here = Path(__file__).resolve().parent
root = here.parent
project = root.parents[1]
sys.path.insert(0, str(root.parent / "M249Orpind20261107/Wrist36"))
import rig

inputs = json.loads((root / "inputs.json").read_text())
result = {}
passed = True
for key in ("M249", "LMG201", "PKM"):
    source = inputs[key]
    names = source["names"]
    donor = source["profiles"]["base" if key == "M249" else "vertical"]
    with gzip.open(here / ("saved_" + key + ".json.gz"), "rt") as stream:
        revised = json.load(stream)
    if key == "M249":
        motion = rig.d["clips"]
    else:
        with gzip.open(root / (key + "_motion.json.gz"), "rt") as stream:
            motion = json.load(stream)
    unchanged = [i for i, n in enumerate(names) if not (n.endswith("_l") and n.startswith(("clavicle","upperarm","lowerarm","hand","thumb","index","middle","ring","pinky")))]
    rows = {}
    passed &= {r["base"] for r in revised["clips"]} == {r["base"] for r in donor["clips"]}
    for row in revised["clips"]:
        path = row["base"]
        times = np.array(motion[path]["times"])
        frames = np.array(motion[path]["frames"])
        a = rig.layer(frames, path, donor, names, times)
        b = rig.layer(frames, path, revised, names, times)
        linear = float(np.max(np.abs(a[:,:,[0,1,2,7,8,9]] - b[:,:,[0,1,2,7,8,9]])))
        rot = Rotation.from_quat(b[:,unchanged,3:7].reshape(-1,4))*Rotation.from_quat(a[:,unchanged,3:7].reshape(-1,4)).inv()
        angle = float(rot.magnitude().max())
        passed &= linear < 1e-5 and angle < 1e-5
        rows[path] = dict(local_translation_scale_max_change=linear,non_left_rotation_change_rad=angle)
    result[key] = rows
mesh = project / "Content/Weapons/M249/SK_M249_V7.uasset"
digest = hashlib.sha256(mesh.read_bytes()).hexdigest()
passed &= digest == "ee0872997aff83a071f3e0764f371dbca6bd38dbe04532e65ae03ad9128aa78d"
accepted = json.loads((root.parent / "M249Orpind20261107/Wrist38/install_receipt.json").read_text())["saved"]
path = "/Game/Weapons/M249/Bipod/DA_M249_SupportGrip"
accepted_ok = hashlib.sha256((project / ("Content/" + path[6:] + ".uasset")).read_bytes()).hexdigest() == accepted[path]
passed &= accepted_ok
for k,rows in result.items():
    print(k,len(rows),max(r["local_translation_scale_max_change"] for r in rows.values()),max(r["non_left_rotation_change_rad"] for r in rows.values()))
print("PASSED",bool(passed),"accepted grip",accepted_ok)
(here / "joint_scope.json").write_text(json.dumps(dict(passed=bool(passed),mesh_sha256=digest,approved_m249_stable_profile_unchanged=accepted_ok,clips=result),indent=2))
if not passed:
    raise SystemExit(1)
