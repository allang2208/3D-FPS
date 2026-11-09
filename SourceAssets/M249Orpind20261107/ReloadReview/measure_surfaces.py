"""Read-only Blender BVH review of the saved, UE-evaluated LOD0 surfaces."""
import json
import os
import pickle
from pathlib import Path
import numpy as np
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree

project = Path(__file__).resolve().parents[3]
folder = Path(os.environ.get("M249_REVIEW_DIR", project / "Saved/M249ReloadReview"))

def load(name):
    with (folder / (name + ".pkl")).open("rb") as stream:
        return pickle.load(stream)

def matrix(row):
    x, y, z, w = row[3:7]
    result = np.eye(4)
    result[:3, :3] = np.asarray(Quaternion((w, x, y, z)).to_matrix()) * row[7:]
    result[:3, 3] = row[:3]
    return result

d = load("geometry")
names = d["names"]
bind = np.asarray([matrix(row) for row in d["bind"]])
inverse_bind = np.linalg.inv(bind)
root = names.index("WPN_root")
indices = {original: i for i, original in enumerate(d["used"])}
vertices = np.asarray(d["vertices"])
faces = np.asarray(d["faces"], dtype=np.int32)
sections = np.asarray(d["sections"])
influences = d["weights"]
dominant = np.array([indices[max(row, key=lambda pair: pair[1])[0]] for row in influences])
primary = dominant[faces[:, 0]]
slot = d["slots"].index

class Surface:
    def __init__(self, select):
        ids, local = np.unique(faces[select].ravel(), return_inverse=True)
        self.tris = local.reshape(-1, 3).tolist()
        self.by_bone = {}
        for i, vi in enumerate(ids):
            for bone, weight in influences[vi]:
                self.by_bone.setdefault(indices[bone], []).append((i, weight))
        self.inputs = []
        for bone, pairs in self.by_bone.items():
            i, w = np.asarray(pairs).T
            i = i.astype(np.int32)
            self.inputs.append((bone, i, np.column_stack((vertices[ids[i]], np.ones(len(i)))) * w[:, None]))
        self.size = len(ids)
        self.labels = [names[n] for n in primary[select]]
        self.rigid = len(self.inputs) == 1
        self.static = self.rigid and self.inputs[0][0] == root
        self.tree = None

    def update(self, transforms):
        if self.static and self.tree is not None:
            return
        if self.rigid:
            bone, _, verts = self.inputs[0]
            self.points = verts @ transforms[bone, :3, :].T
        else:
            self.points = np.zeros((self.size, 3))
            for bone, ids, verts in self.inputs:
                self.points[ids] += verts @ transforms[bone, :3, :].T
        self.low = self.points.min(axis=0)
        self.high = self.points.max(axis=0)
        self.tree = BVHTree.FromPolygons(self.points.tolist(), self.tris, all_triangles=True)

def hand(side):
    side_ids = [i for i, name in enumerate(names) if name.endswith("_" + side)]
    return Surface((sections == slot("Skin_Hand")) & np.isin(primary, side_ids))

hands = {"left": hand("l"), "right": hand("r")}
fixed = {"body": Surface(primary == root), "cover": Surface(primary == names.index("PKM_Cover")),
         "tray": Surface(primary == names.index("PKM_Tray"))}
belts = {}
boxes = {}
for state in ("Old", "New"):
    belts[state] = Surface(np.isin(sections, [i for i, name in enumerate(d["slots"]) if name.endswith("__" + state + "Belt")]))
    boxes[state] = Surface(sections == slot("M249_Surface__" + state + "Box"))

def transforms(row):
    world = np.asarray([matrix(v) for v in row])
    return bind[root] @ np.linalg.inv(world[root]) @ world @ inverse_bind

def contacts(belt, other):
    delta = np.maximum(belt.low - other.high, other.low - belt.high)
    if np.any(delta > 0):
        return [], float(np.linalg.norm(np.maximum(0, delta)))
    pairs = belt.tree.overlap(other.tree)
    return sorted({belt.labels[i].split("PKM_")[-1] for i, j in pairs}), 0.

def hand_gap(belt, surface, box_gap, dense):
    # Any pair of points proves an upper bound; a separating plane proves a lower bound.
    candidates = surface.points[::32]
    nearest = [belt.tree.find_nearest(p) for p in candidates]
    idx = min(range(len(nearest)), key=lambda i: nearest[i][3])
    q, _, _, upper = nearest[idx]
    delta = candidates[idx] - np.asarray(q)
    if upper:
        direction = delta / upper
        box_gap = max(box_gap, float((surface.points @ direction).min() - (belt.points @ direction).max()))
    if dense:
        for a,b in ((surface,belt),(belt,surface)):
            region = np.all((a.points >= b.low-upper) & (a.points <= b.high+upper),axis=1)
            for p in a.points[region]:
                hit = b.tree.find_nearest(p,upper)
                if hit[3] is not None:
                    upper = min(upper,hit[3])
    return [round(box_gap, 3), round(upper, 3)]

summary = {}
idle_pose = transforms(load("idle")[1][0])
belts["Old"].update(idle_pose)
def centers(belt):
    return {names[i].split("PKM_")[-1]: belt.points[ids].mean(axis=0) for i, ids, _ in belt.inputs}
idle_centers = centers(belts["Old"])
for role in ("reload", "reload_empty"):
    times, frames = load(role)
    skip = .9 if role == "reload_empty" else 0.
    rows = []
    boundaries = (3.2 - skip, 3.55 - skip)
    for index in range(len(times)):
        time = times[index]
        state = "Old" if role == "reload" and time < boundaries[0] - 1e-5 else "New" if time >= boundaries[1] - 1e-5 else None
        row = {"frame": index, "time": round(time, 5), "visible": state}
        if state:
            pose = transforms(frames[index])
            belt = belts[state]
            belt.update(pose)
            others = {**hands, **fixed, "box": boxes[state]}
            for key, other in others.items():
                other.update(pose)
                hits, lower = contacts(belt, other)
                row[key] = {"crossing": hits}
                if key in hands:
                    dense = (key == "left" and state == "Old" and 1.35 <= time <= 2.03) or (
                             key == "right" and state == "New" and 4.49-skip <= time <= 5.13-skip)
                    row[key]["gap_cm"] = [0, 0] if hits else hand_gap(belt, other, lower, dense)
            for key, surface in hands.items():
                if (key == "left" and state == "Old" and 1.25 <= time <= 2.12) or (
                        key == "right" and state == "New" and 4.37-skip <= time <= 5.26-skip):
                    row[key]["other_crossings"] = {k:len(surface.tree.overlap(others[k].tree))
                                                for k in ("body","cover","tray","box")}
            if index == len(times) - 1:
                row["idle_handoff_max_cm"] = round(max(np.linalg.norm(v - idle_centers[k]) for k, v in centers(belt).items()), 4)
        rows.append(row)
    summary[role] = rows
    (folder / "contacts.json").write_text(json.dumps(summary, indent=1))
    print("M249_SURFACES", role, len(rows), flush=True)
