"""Measure bare-skin and sewn-cuff longitudinal overlap on native M870 action samples."""
import gzip
import json

import numpy as np

from bare_wrist_review import ROOT, SET, load
from native_glove_review import Skin, component


def main():
    source = SET / "NativeGloveR1/Read"
    pose = json.load(gzip.open(source / "M870_poses.json.gz", "rt"))
    names = pose["names"]
    parents = [names.index(n) if n in names else -1 for n in pose["parents"]]
    cloth_mesh = load(SET / "CombatShirtR4/Authored/shirt_fp_Super90.json")
    cuff = Skin(cloth_mesh, names, False)
    cf = np.unique(cuff.faces[cuff.mats == cloth_mesh["material_slots"].index("CombatCuff")])
    output = {}
    for body in ("Jason", "Kaitlin"):
        native = load(source / ("M870_"+body+".json"))
        skin = Skin(native, names, False)
        slots = native["material_slots"]
        arm = np.unique(skin.faces[skin.mats == slots.index("Manny_S90_Skin_Forearm")])
        hand = np.unique(skin.faces[skin.mats == slots.index("Manny_S90_Skin_Hand")])
        sectors = []
        for side in "lr":
            h = names.index("hand_"+side)
            e = names.index("lowerarm_"+side)
            w = np.array(native["bones"][names[h]]["position"])
            axis = np.array(native["bones"][names[e]]["position"]) - w
            axis /= np.linalg.norm(axis)
            radial = np.cross(axis, np.eye(3)[np.argmin(abs(axis))])
            radial /= np.linalg.norm(radial)
            other = np.cross(axis, radial)
            def groups(points, ids, maximum):
                delta = points[ids]-w
                keep = np.linalg.norm(delta, axis=1)<maximum
                ids, delta = ids[keep], delta[keep]
                sector = ((np.arctan2(delta@other,delta@radial)+np.pi)*16/(2*np.pi)).astype(int)%16
                return [ids[sector==i] for i in range(16)]
            # The selected band is entirely inside the shader's fully opaque radius.
            cloth_ids, base_ids, band_ids = groups(cuff.points,cf,15),groups(skin.points,hand,6),groups(skin.points,arm,10.5)
            sectors.append((h,e,[(c,s,b) for c,s,b in zip(cloth_ids,base_ids,band_ids) if len(c)*len(s)*len(b)]))
        report = {}
        for name, clip in pose["clips"].items():
            min_before, min_after, open_before, open_after, total = np.inf, np.inf, 0, 0, 0
            for local in clip["local"]:
                matrices = component(local,parents)
                cloth_pts, skin_pts = cuff.skin(matrices), skin.skin(matrices)
                for h,e,parts in sectors:
                    axis = matrices[e,:3,3]-matrices[h,:3,3]
                    axis /= np.linalg.norm(axis)
                    for c,s,b in parts:
                        rim = np.min(cloth_pts[c]@axis)
                        old = np.max(skin_pts[s]@axis)-rim
                        new = max(old,np.max(skin_pts[b]@axis)-rim)
                        min_before, min_after = min(old,min_before), min(new,min_after)
                        open_before += int(old<0)
                        open_after += int(new<0)
                        total += 1
            report[name] = dict(samples=len(clip["local"]), sector_samples=total, before_open=open_before,
                                after_open=open_after, min_before_cm=round(min_before,3), min_after_cm=round(min_after,3))
        output[body] = report
    (ROOT/"m870-posed-wrist-review.json").write_text(json.dumps(dict(
        method="Native LBS, 16 reference sectors per wrist, conservative fully opaque mask radius, sampled sequences",
        corrective_morphs_evaluated=False, gameplay_tested=False, bodies=output),indent=2))
    for sex,clips in output.items():
        print(sex,len(clips),sum(r["samples"] for r in clips.values()),sum(r["before_open"] for r in clips.values()),
              sum(r["after_open"] for r in clips.values()),min(r["min_after_cm"] for r in clips.values()))


if __name__ == "__main__":
    main()
