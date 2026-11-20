"""Read the two equipped full-set torso meshes after the November shoulder refit."""
import json
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
SET = PROJECT / "SourceAssets/ModernTacticalSet20261113"
REVIEW = SET / "HelmetNapeR3/Review"
REVISIONS = {"R2": "HelmetContourR2", "R3": "HelmetNapeR3"}


def read(path):
    return json.loads(Path(path).read_bytes())


def torso(rig):
    old_route = read(SET/"SetReview20261118/body-fit.json")[rig]["equipped"][0]
    new_route = old_route.replace("/CombatShirtR4/", "/ShoulderFit20261118/")
    if new_route not in read(SET/"ShoulderFit20261118/published.json")["packages"]:
        raise ValueError(f"Missing published fitted garment {new_route}")
    row = next(r for r in read(SET/"CombatShirtR4/authored.json")["rows"] if r["asset"] == old_route.split(".")[0])
    garment = read(row["file"])
    mapping = {}
    for label in ("cloth","carrier"):
        edits = np.load(SET/"ShoulderFit20261118"/f"{rig}-{label}.npz")
        mapping.update({p.tobytes(): q for p,q in zip(edits["before"].astype("<f4"),edits["after"])})
    points = np.asarray(garment["positions"], dtype="<f4")
    garment["positions"] = np.array([mapping.get(p.tobytes(),p) for p in points])
    return garment
