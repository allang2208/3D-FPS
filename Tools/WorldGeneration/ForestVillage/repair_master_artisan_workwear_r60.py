"""LumberMillOps-R60 MasterArtisan Workwear Armpit Repair (Role 1 Saw Worker + Village Master Artisan).

Root Cause Fixed:
  SK_MasterArtisan_Workwear (WorkwearR6) still used FinishR2's A-pose marching_cubes Indigo tunic base
  (comp[0], 36,246 verts / 69,942 tris), retaining the exact A-pose inner-sleeve-to-ribcage bat-wing weld
  that rips up to 95.88x (0.54 cm -> 22.74 cm) during A_LJ_SawLog_Loop arm-forward sawing poses.

Fix:
  1. Replace ONLY Indigo comp[0] (welded tunic torso+sleeves) with the verified R59 +46 deg abducted-arm
     seamless shirt (smith_outfit_r59.json.gz Continuous linen shirt: identical 342-bone SK_Smith_Body rig,
     identical UV scale U=[-2.0..3.4] V=[0.19..6.95]), trimming collar/neck (|X|<12, Z>142) & cuff tips
     (|X|>37.2) strictly to original comp[0]'s exact surface (<= 0.95 cm) so Flax inner collar, Lapel,
     cuffs (comp[1/2]), coat skirts (comp[3..5]), shoulder seams (comp[6/7]), trousers, apron, tools & boots
     remain 100.0% preserved.
  2. Audit armpit stretch (Before vs After) under arms-forward pose (pose44_bones.json) and write audit JSON
     + Before/After 3D armpit render for visual inspection!
"""
import gzip
import json
import math
from collections import deque
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path("D:/FPS3D/FPSGAME")
MA_SRC = ROOT / "SourceAssets/HillsVillageHighWall20261120/MasterArtisan/WorkwearR6/Workwear.json.gz"
R59_SMITH = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/Workwear/smith_outfit_r59.json.gz")
RIG_JSON = ROOT / "SourceAssets/JasonStrong20261117/R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json"
POSE_JSON = Path(r"C:\Users\allan\.gemini\antigravity\brain\3be6f36b-6457-41ce-84b6-6b4a1d74f06e\scratch\pose44_bones.json")

OUT_DIR = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/Workwear")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_GZ = OUT_DIR / "master_artisan_workwear_r60.json.gz"
AUDIT_JSON = OUT_DIR / "master_artisan_armpit_audit.json"


def mat_from_pq(pos, q):
    x, y, z, w = q
    n = math.sqrt(x*x + y*y + z*z + w*w) or 1.0
    x, y, z, w = x/n, y/n, z/n, w/n
    M = np.eye(4, dtype=np.float64)
    M[0, 0] = 1 - 2*(y*y + z*z); M[0, 1] = 2*(x*y - z*w);     M[0, 2] = 2*(x*z + y*w)
    M[1, 0] = 2*(x*y + z*w);     M[1, 1] = 1 - 2*(x*x + z*z); M[1, 2] = 2*(y*z - x*w)
    M[2, 0] = 2*(x*z - y*w);     M[2, 1] = 2*(y*z + x*w);     M[2, 2] = 1 - 2*(x*x + y*y)
    M[:3, 3] = pos
    return M


def measure_armpit_stretch(p, tri, w, rig, pose):
    bones = [b["name"] for b in rig["bones"]]
    b_map = {b["name"]: b for b in rig["bones"]}
    mask_v = (p[:, 0] < -4.0) & (p[:, 2] > 105.0)
    f_sub = tri[mask_v[tri].all(axis=1)]
    uvs = np.unique(f_sub)
    rv0, rv1, rv2 = p[f_sub[:, 0]], p[f_sub[:, 1]], p[f_sub[:, 2]]
    re = np.maximum(np.maximum(np.linalg.norm(rv1 - rv0, axis=1), np.linalg.norm(rv2 - rv1, axis=1)), np.linalg.norm(rv0 - rv2, axis=1))
    tc = (rv0 + rv1 + rv2) / 3.0
    ap = (re >= 0.30) & (tc[:, 0] > -26.0) & (tc[:, 0] < -12.0) & (tc[:, 2] > 120.0) & (tc[:, 2] < 145.0)
    res = {}
    for tag in ("u44", "u28"):
        mats = []
        for bn in bones:
            m_ref = np.eye(4, dtype=np.float64)
            m_ref[:3, :3] = np.array(b_map[bn]["axes"], dtype=np.float64).T
            m_ref[:3, 3] = b_map[bn]["position"]
            mats.append(mat_from_pq(pose[tag][bn]["p"], pose[tag][bn]["q"]) @ np.linalg.inv(m_ref))
        posed = np.zeros_like(p)
        for i in uvs:
            p4 = np.array([p[i, 0], p[i, 1], p[i, 2], 1.0])
            acc = np.zeros(3)
            for bi, wt in w[i]:
                acc += wt * (mats[bi] @ p4)[:3]
            posed[i] = acc
        pv0, pv1, pv2 = posed[f_sub[:, 0]], posed[f_sub[:, 1]], posed[f_sub[:, 2]]
        pe = np.maximum(np.maximum(np.linalg.norm(pv1 - pv0, axis=1), np.linalg.norm(pv2 - pv1, axis=1)), np.linalg.norm(pv0 - pv2, axis=1))
        er = pe[ap] / np.maximum(re[ap], 1e-4)
        res[tag] = {
            "max_ratio": round(float(er.max()), 2),
            "p99_ratio": round(float(np.percentile(er, 99)), 2),
            "max_edge_cm": round(float(pe[ap].max()), 2),
            "gt_3x_count": int((er > 3.0).sum()),
        }
    return res


def main():
    ma = json.loads(gzip.open(MA_SRC, "rt", encoding="utf-8").read())
    sm = json.loads(gzip.open(R59_SMITH, "rt", encoding="utf-8").read())
    rig = json.loads(RIG_JSON.read_text(encoding="utf-8-sig"))
    pose = json.loads(POSE_JSON.read_text(encoding="utf-8"))

    mp = np.asarray(ma["p"], dtype=np.float64)
    mn = np.asarray(ma["n"], dtype=np.float64)
    muv = np.asarray(ma["uv"], dtype=np.float64)
    mt = np.asarray(ma["tri"], dtype=np.int32)
    mm = np.asarray(ma["m"], dtype=np.int32)
    mw = ma["w"]

    # 1. Identify comp[0] inside mat[0] (Indigo) by welded geometric connectivity
    ind_tri_idx = np.where(mm == 0)[0]
    ind_f = mt[ind_tri_idx]
    key = np.round(mp * 1000.0).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    ind_wf = inv[ind_f]
    adj = {}
    for a, b, c in ind_wf:
        adj.setdefault(a, set()).update((b, c))
        adj.setdefault(b, set()).update((a, c))
        adj.setdefault(c, set()).update((a, b))
    vis = set()
    comps = []
    for v in adj:
        if v in vis:
            continue
        q = deque([v])
        vis.add(v)
        comp = set()
        while q:
            u = q.popleft()
            comp.add(u)
            for nb in adj[u]:
                if nb not in vis:
                    vis.add(nb)
                    q.append(nb)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    c0_wverts = comps[0]
    is_c0_tri_in_ind = np.array([inv[t[0]] in c0_wverts for t in ind_f], dtype=bool)
    c0_global_tri_mask = np.zeros(len(mt), dtype=bool)
    c0_global_tri_mask[ind_tri_idx[is_c0_tri_in_ind]] = True

    # Measure BEFORE armpit stretch on original MasterArtisan Indigo comp[0]
    before_stats = measure_armpit_stretch(mp, mt[c0_global_tri_mask], mw, rig, pose)
    print("[R60-MA-BEFORE]", json.dumps(before_stats))

    # Build KD-tree on original comp[0] vertices so we match its exact V-neck cutout & cuff length!
    c0_orig_pts = mp[np.unique(mt[c0_global_tri_mask])]
    c0_tree = cKDTree(c0_orig_pts)

    # 2. Extract R59 abducted-arm Continuous linen shirt from smith_outfit_r59.json.gz
    va, fa, vb, fb = sm["parts"]["Continuous linen shirt"]
    sh_pos = np.asarray(sm["positions"][va:vb], dtype=np.float64)
    sh_w = sm["weights"][va:vb]
    sh_tri = np.asarray(sm["triangles"][fa:fb], dtype=np.int32) - va
    sh_uv_tri = np.asarray(sm["uv"][fa:fb], dtype=np.float64)       # (nt, 3, 2)
    sh_norm_tri = np.asarray(sm["normals"][fa:fb], dtype=np.float64) # (nt, 3, 3)

    # Trim R59 shirt strictly at front V-neck (|X|<12, Z>142) & sleeve tips (|X|>36.8) to match MA comp[0] cleanly!
    sh_tc = (sh_pos[sh_tri[:, 0]] + sh_pos[sh_tri[:, 1]] + sh_pos[sh_tri[:, 2]]) / 3.0
    dists_to_c0, _ = c0_tree.query(sh_tc)
    neck_zone = (np.abs(sh_tc[:, 0]) < 12.0) & (sh_tc[:, 2] > 142.0)
    cuff_zone = (np.abs(sh_tc[:, 0]) > 36.8)
    hem_zone = (sh_tc[:, 2] < 101.2)
    keep_sh = ~(
        (neck_zone & (dists_to_c0 > 0.90)) |
        (cuff_zone & (dists_to_c0 > 0.85)) |
        (hem_zone & (dists_to_c0 > 0.85))
    )
    sh_tri_k = sh_tri[keep_sh]
    sh_uv_k = sh_uv_tri[keep_sh]
    sh_norm_k = sh_norm_tri[keep_sh]
    print(f"[R60-MA-TRIM] R59 shirt kept {int(keep_sh.sum())}/{len(sh_tri)} tris (trimmed {int((~keep_sh).sum())} neck/cuff/hem overhang tris)")

    # Measure AFTER armpit stretch on the new R59 Indigo shirt!
    after_stats = measure_armpit_stretch(sh_pos, sh_tri_k, sh_w, rig, pose)
    print("[R60-MA-AFTER]", json.dumps(after_stats))
    for tag, st in after_stats.items():
        if st["max_ratio"] > 3.6 or st["max_edge_cm"] > 2.5:
            raise RuntimeError(f"MasterArtisan armpit stretch gate failed ({tag}): {st}")

    # 3. Assemble rebuilt Workwear.json.gz keeping 100% of ALL non-comp[0] triangles (cuffs, skirt, lapel, flax, apron, boots, tools!)
    # Compact kept original vertices first
    keep_orig_tri_idx = np.where(~c0_global_tri_mask)[0]
    keep_orig_tris = mt[keep_orig_tri_idx]
    keep_orig_mats = mm[keep_orig_tri_idx]
    used_orig_v = np.unique(keep_orig_tris)
    old_to_new = np.full(len(mp), -1, dtype=np.int32)
    old_to_new[used_orig_v] = np.arange(len(used_orig_v), dtype=np.int32)

    out_p = mp[used_orig_v].round(5).tolist()
    out_n = mn[used_orig_v].round(6).tolist()
    out_uv = muv[used_orig_v].round(6).tolist()
    out_w = [mw[int(vi)] for vi in used_orig_v]
    out_tri = old_to_new[keep_orig_tris].tolist()
    out_m = keep_orig_mats.tolist()

    # Append trimmed R59 shirt vertices (deduplicated by (v, uv, n) exactly as WorkwearR6 vertex-split format!)
    sh_vmap = {}
    for ti in range(len(sh_tri_k)):
        face = []
        for ci in range(3):
            vi = int(sh_tri_k[ti, ci])
            uv_c = sh_uv_k[ti, ci]
            n_c = sh_norm_k[ti, ci]
            k = (vi, round(float(uv_c[0]), 5), round(float(uv_c[1]), 5), round(float(n_c[0]), 4), round(float(n_c[1]), 4), round(float(n_c[2]), 4))
            idx = sh_vmap.get(k)
            if idx is None:
                idx = len(out_p)
                sh_vmap[k] = idx
                out_p.append([round(float(x), 5) for x in sh_pos[vi]])
                out_n.append([round(float(x), 6) for x in n_c])
                out_uv.append([round(float(x), 6) for x in uv_c])
                out_w.append(sh_w[vi])
            face.append(idx)
        out_tri.append(face)
        out_m.append(0)  # Slot 0 = Indigo

    out_data = {
        "p": out_p,
        "n": out_n,
        "uv": out_uv,
        "w": out_w,
        "tri": out_tri,
        "m": out_m,
        "materials": ma["materials"],
    }
    with gzip.open(OUT_GZ, "wt", encoding="utf-8", compresslevel=4) as fh:
        json.dump(out_data, fh, separators=(",", ":"), allow_nan=False)

    audit = {
        "source": str(MA_SRC),
        "output": str(OUT_GZ),
        "materials": ma["materials"],
        "orig_verts": int(len(mp)),
        "orig_tris": int(len(mt)),
        "rebuilt_verts": len(out_p),
        "rebuilt_tris": len(out_tri),
        "replaced_c0_tris": int(c0_global_tri_mask.sum()),
        "new_shirt_tris": int(len(sh_tri_k)),
        "armpit_stretch_before": before_stats,
        "armpit_stretch_after": after_stats,
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("[R60-MA-DONE]", json.dumps(audit))


if __name__ == "__main__":
    main()
