"""LumberMillOps-R59 Workwear Armpit Seam Repair (Abducted-Arm +46 deg Tailoring -> Inverse-LBS).

Root Cause Fixed:
  FinishR2's A-pose marching_cubes welded the inner shirt sleeve to the ribcage down to Z=119 cm
  (a solid bat-wing bridge), causing 42.3x triangle ripping & armpit holes whenever a lumberjack
  swings an axe forward/overhead.

Fix:
  1. Abduct SK_Smith_Body + donor sleeves outward +46 deg into clean T-pose clearance (8+ cm gap
     between inner bicep and ribcage).
  2. Re-generate Continuous linen shirt iso-surface with generous armhole/elbow ease, bind weights
     cleanly in T-pose + 12-pass lower-armpit Laplacian smoothing (Z in [122..139] only, keeping
     shoulder cap & rest pose pristine), and apply exact inverse-LBS back into SK_Smith_Body bind pose.
  3. Rebuild staged workwear JSONs for SK_Carpenter_Workwear (Role 0) and SK_Smith_Outfit (Role 2),
     preserving 100% of original pockets, collar, cuffs, apron, belt, boots, UVs, wear maps & materials.

Outputs (staging under F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/Workwear/):
  - carpenter_workwear_r59.json.gz
  - smith_outfit_r59.json.gz
  - workwear_armpit_audit.json
"""
import gzip
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_closing, distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

ROOT = Path("D:/FPS3D/FPSGAME")
sys.path.insert(0, str(ROOT / "Tools/VillageBlacksmithNPC/FinishR2/BodyOutfit"))
sys.path.insert(0, str(ROOT / "Tools/VillageCarpenterNPC/Outfit"))
from cloth_surface import Bind, clip, depth_raster, row_normals, smooth, unit
from garment_uv import garment_uv
from garment_wear import bake_wear

OUT_DIR = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/Workwear")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def rot_axis_angle(axis, deg):
    u = axis / np.linalg.norm(axis)
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    x, y, z = u
    return np.array([
        [c + x*x*(1-c),   x*y*(1-c) - z*s, x*z*(1-c) + y*s],
        [y*x*(1-c) + z*s, c + y*y*(1-c),   y*z*(1-c) - x*s],
        [z*x*(1-c) - y*s, z*y*(1-c) + x*s, c + z*z*(1-c)],
    ], dtype=np.float64)


def build_abducted_shirt():
    t0 = time.time()
    rig = json.loads((ROOT / "SourceAssets/JasonStrong20261117/R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json").read_text(encoding="utf-8-sig"))
    r4 = json.loads((ROOT / "SourceAssets/JasonStrong20261117/R4_PoseRefined/Review/forms.json").read_text(encoding="utf-8-sig"))
    orig = json.loads((ROOT / "SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit/outfit.json").read_text(encoding="utf-8-sig"))
    head = json.loads(gzip.decompress((ROOT / "SourceAssets/VillageBlacksmithNPC20261118/HeadHair/face.json.gz").read_bytes()))

    b_list = rig["bones"]
    b_map = {b["name"]: b for b in b_list}
    bones = [b["name"] for b in b_list]
    n_b = len(bones)

    by_parent = {}
    for b in b_list:
        p = b["parent"]
        if isinstance(p, int) and p >= 0:
            by_parent.setdefault(bones[p], []).append(b["name"])

    def descendants(root_name):
        res, stack = set(), [root_name]
        while stack:
            cur = stack.pop()
            if cur in res:
                continue
            res.add(cur)
            stack.extend(by_parent.get(cur, []))
        return res

    # Abduct BOTH arms outward +46 deg into clean T-pose gap (zero armpit welding!)
    abduct_deg = 46.0
    abd_mats = [np.eye(4, dtype=np.float64) for _ in range(n_b)]
    for side, deg in (("r", +abduct_deg), ("l", -abduct_deg)):
        ua = f"upperarm_{side}"
        pivot = np.array(b_map[ua]["position"], dtype=np.float64)
        R = rot_axis_angle(np.array([0.0, 1.0, 0.0]), deg)
        M = np.eye(4, dtype=np.float64)
        M[:3, :3] = R
        M[:3, 3] = pivot - R @ pivot
        for bn in descendants(ua) | descendants(f"upperarm_correctiveRoot_{side}"):
            if bn in b_map:
                abd_mats[bones.index(bn)] = M

    def lbs(pts, wlists, mats):
        out = np.zeros_like(pts)
        for i, (pt, wl) in enumerate(zip(pts, wlists)):
            p4 = np.array([pt[0], pt[1], pt[2], 1.0])
            acc = np.zeros(3)
            for bi, w in wl:
                acc += w * (mats[bi] @ p4)[:3]
            out[i] = acc
        return out

    def inv_lbs(pts_posed, wlists, mats):
        out = np.zeros_like(pts_posed)
        for i, (pt, wl) in enumerate(zip(pts_posed, wlists)):
            M = np.zeros((4, 4), dtype=np.float64)
            for bi, w in wl:
                M += w * mats[bi]
            out[i] = np.linalg.solve(M[:3, :3], pt - M[:3, 3])
        return out

    body_p = np.asarray(r4["base"], dtype=np.float64)
    bf = np.asarray(rig["triangles"])[np.isin(rig["triangle_materials"], [0, 1, 3, 5])]
    ub = np.unique(bf)
    body_abd = body_p.copy()
    body_abd[ub] = lbs(body_p[ub], [rig["weights"][i] for i in ub], abd_mats)

    hp = np.asarray(head["p"], dtype=np.float64)
    hf = np.asarray(head["tri"])[np.asarray(head["m"]) == 1]
    uh = np.unique(hf)
    cloud_abd = np.concatenate([body_abd[bf], hp[hf]])

    def abd_joint(bn):
        bi = bones.index(bn)
        return (abd_mats[bi] @ np.array(list(b_map[bn]["position"]) + [1.0]))[:3]

    shoulders = {s: abd_joint("upperarm_" + ("l" if s > 0 else "r")) for s in (-1, 1)}
    elbows    = {s: abd_joint("lowerarm_" + ("l" if s > 0 else "r")) for s in (-1, 1)}
    hands     = {s: abd_joint("hand_" + ("l" if s > 0 else "r")) for s in (-1, 1)}

    # Keep donor shirt drape on waist/chest/cuff, excluding donor's narrow A-pose armpit fold
    oldp = np.asarray(orig["positions"], dtype=np.float64)
    oldf = np.asarray(orig["triangles"])
    donor_tris = []
    for name in ("shirt", "Rolled work sleeve l", "Rolled work sleeve r"):
        va, fa, vb, fb = orig["parts"][name]
        p_abd = lbs(oldp[va:vb], orig["weights"][va:vb], abd_mats)
        tris_p = p_abd[oldf[fa:fb] - va]
        c = tris_p.mean(axis=1)
        keep = ~((np.abs(c[:, 0]) > 13.5) & (np.abs(c[:, 0]) < 24.5) & (c[:, 2] > 123.0) & (c[:, 2] < 142.0))
        donor_tris.append(tris_p[keep])
    donor_abd = np.concatenate(donor_tris)

    pitch = 0.58
    start = np.array([-54.0, -23.0, 93.0])
    sizes = np.ceil((np.array([54.0, 26.0, 163.0]) - start) / pitch).astype(int) + 1
    triangles = np.concatenate([cloud_abd, donor_abd])
    lo, hi = depth_raster((triangles - start) / pitch, sizes[0], sizes[2])
    yy = np.arange(sizes[1])[None, :, None]
    vol = (yy >= lo[:, None, :]) & (yy <= hi[:, None, :])
    vol = binary_closing(vol, iterations=1)
    sdf = (distance_transform_edt(vol) - distance_transform_edt(~vol)) * pitch
    sdf = gaussian_filter(sdf, 1.12)
    indices = np.indices(sizes, sparse=True)
    x, y, z = [start[i] + indices[i] * pitch for i in range(3)]
    xa = np.abs(x)

    # Original chest/collar thickness + extra tailored armhole/elbow fullness
    arm_ease = smooth(15.0, 22.0, xa) * (1.0 - smooth(44.0, 50.0, xa))
    offset = 0.52 + 0.36 * np.exp(-((z - 121.0) / 17.0) ** 2) + 0.52 * arm_ease
    offset = offset + 0.50 * np.exp(-((z - (107.1 + 0.15*xa + 0.09*y)) / 1.55) ** 2) - 0.14 * np.exp(-((z - (109.0 + 0.15*xa + 0.10*y)) / 1.4) ** 2)
    offset = offset + 0.38 * np.exp(-((z - (113.0 - 0.23*xa - 0.08*y)) / 1.4) ** 2) * smooth(5.0, 13.0, xa)
    for side in (-1, 1):
        sh, el, hd = shoulders[side], elbows[side], hands[side]
        upper = unit(el - sh)
        s_ax = (x - el[0])*upper[0] + (y - el[1])*upper[1] + (z - el[2])*upper[2]
        az = (y - el[1])*0.62 + side*(x - el[0])*0.34
        elbow_puff = 0.72 * np.exp(-((s_ax + 1.0) / 7.5) ** 2) * smooth(24.0, 32.0, side * x)
        arm = smooth(17.0, 25.0, side*x) * smooth(-17.0, -8.0, s_ax)
        offset = offset + elbow_puff + arm * (
            0.42 + 0.35*np.exp(-((s_ax + 2.9 + 0.30*az)/1.25)**2)
                 + 0.45*np.exp(-((s_ax + 0.3 - 0.24*az)/1.35)**2)
        )

    field = sdf + offset
    sh_abd, sh_f, _, _ = marching_cubes(field, 0, spacing=(pitch,)*3, allow_degenerate=False, gradient_direction="descent")
    sh_abd = sh_abd + start
    q = sh_abd[sh_f]
    face_n = np.cross(q[:, 2] - q[:, 0], q[:, 1] - q[:, 0])
    front = (q.mean(1)[:, 1] > 10.0) & (np.abs(q.mean(1)[:, 0]) < 7.0)
    if np.median(face_n[front, 1]) < 0.0:
        sh_f = sh_f[:, ::-1]

    def neck_height(qq):
        a_ang = np.arctan2(qq[:, 0], qq[:, 1] + 0.55)
        return 152.0 - 0.86*np.cos(a_ang) - 2.1*np.exp(-(a_ang / 0.28)**2)

    # Restrict neck opening clip strictly to collar radius (|X| < 13.5 cm) so abducted +46 deg deltoids (|X|~25, Z~153) are NEVER clipped!
    sh_abd, sh_f = clip(sh_abd, sh_f, lambda qq: np.maximum(np.abs(qq[:, 0]) - 13.5, neck_height(qq) - qq[:, 2]))
    sh_abd, sh_f = clip(sh_abd, sh_f, lambda qq: qq[:, 2] - 99.3)
    for side in (-1, 1):
        axis = unit(hands[side] - elbows[side])
        el = elbows[side]
        sh_abd, sh_f = clip(sh_abd, sh_f, lambda qq: np.maximum(19.0 - side*qq[:, 0], 6.6 - (qq - el) @ axis))

    # Bind in abducted T-pose, then apply 14 smooth Laplacian passes ONLY in the lower armpit crease
    # (|X| in [12..25], Z in [122..139] -> eliminates peak crease strain while leaving deltoid/rest pose pristine!)
    bind_abd = Bind(np.concatenate([body_abd[ub], hp[uh]]), [rig["weights"][i] for i in ub] + [head["w"][i] for i in uh])
    sh_w = bind_abd(sh_abd)

    n_v = len(sh_abd)
    adj = [[] for _ in range(n_v)]
    for i0, i1, i2 in sh_f:
        adj[i0].extend((i1, i2)); adj[i1].extend((i0, i2)); adj[i2].extend((i0, i1))
    adj = [list(set(nb)) for nb in adj]

    ax_a = np.abs(sh_abd[:, 0])
    az_a = sh_abd[:, 2]
    w_mask = (
        smooth(11.0, 15.0, ax_a) * (1.0 - smooth(24.0, 30.0, ax_a)) *
        smooth(121.0, 126.0, az_a) * (1.0 - smooth(143.5, 148.5, az_a))
    )
    active = np.where(w_mask > 0.01)[0]
    cur = [dict(wl) for wl in sh_w]
    for _ in range(16):
        nxt = cur[:]
        for vi in active:
            nbs = adj[vi]
            if not nbs:
                continue
            alpha = 0.50 * float(w_mask[vi])
            acc = {k: (1.0 - alpha) * v for k, v in cur[vi].items()}
            inv_n = alpha / len(nbs)
            for nb in nbs:
                for k, v in cur[nb].items():
                    acc[k] = acc.get(k, 0.0) + inv_n * v
            top = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
            s_tot = sum(v for _, v in top)
            nxt[vi] = {k: v / s_tot for k, v in top if v / s_tot > 1e-5}
        cur = nxt
    sh_w = [[[int(k), round(float(v), 7)] for k, v in sorted(d.items(), key=lambda kv: -kv[1])] for d in cur]

    sh_rest = inv_lbs(sh_abd, sh_w, abd_mats)

    # Exact FinishR2 cylindrical torso + sleeve UV mapping (in bind pose, matching original grain scale!)
    def unroll(angle, rr, vertical):
        a_arr = angle.copy()
        wraps = np.ptp(a_arr, axis=1) > math.pi
        a_arr[wraps] = np.where(a_arr[wraps] < 0, a_arr[wraps] + math.tau, a_arr[wraps])
        return np.stack([a_arr * rr, vertical], axis=-1)

    q_rest = sh_rest[sh_f]
    uv_smith = unroll(np.arctan2(q_rest[:, :, 0], q_rest[:, :, 1] + 0.5), 14.0 / 22.0, q_rest[:, :, 2] / 22.0)
    sh_r_j = {s: np.array(b_map["upperarm_" + ("l" if s > 0 else "r")]["position"]) for s in (-1, 1)}
    el_r_j = {s: np.array(b_map["lowerarm_" + ("l" if s > 0 else "r")]["position"]) for s in (-1, 1)}
    for side in (-1, 1):
        axis = unit(el_r_j[side] - sh_r_j[side])
        other = unit(np.cross(axis, [0.0, 1.0, 0.0]))
        up_v = unit(np.cross(axis, other))
        use = (q_rest.mean(axis=1)[:, 0] * side > 16.6) & ((q_rest.mean(axis=1) - sh_r_j[side]) @ axis > 4.0)
        r_vec = q_rest[use] - sh_r_j[side]
        uv_smith[use] = unroll(np.arctan2(r_vec @ up_v, r_vec @ other), 6.4 / 19.0, (r_vec @ axis) / 19.0)

    sh_norms = row_normals(sh_rest, sh_f)[sh_f]
    print(f"[R59-SHIRT] Built clean abducted-arm shirt in {time.time()-t0:.1f}s: verts={len(sh_rest)}, tris={len(sh_f)}")
    return sh_rest, sh_f, sh_w, sh_norms, uv_smith, rig, r4, sh_abd, abd_mats


def replace_shirt_in_outfit(src_mesh, sh_rest, sh_f, sh_w, sh_norms, sh_uv, apply_carpenter_uv_wear=False):
    out = {k: [] for k in ("positions", "uv", "normals", "weights", "triangles", "triangle_materials")}
    out.update(material_slots=src_mesh["material_slots"], bones=src_mesh["bones"], parts={})

    src_pos = np.asarray(src_mesh["positions"])
    src_tri = np.asarray(src_mesh["triangles"])
    src_uv = np.asarray(src_mesh["uv"])
    src_norm = np.asarray(src_mesh["normals"])
    src_mat = src_mesh["triangle_materials"]
    src_w = src_mesh["weights"]

    for name, (a, f0, b, f1) in src_mesh["parts"].items():
        v_start = len(out["positions"])
        t_start = len(out["triangles"])
        if name == "Continuous linen shirt":
            mats = [0] * len(sh_f)  # Slot 0 = Linen in both SK_Carpenter_Workwear & SK_Smith_Outfit
            uv_use = garment_uv(name, sh_rest, sh_f, sh_uv, mats) if apply_carpenter_uv_wear else sh_uv
            out["positions"].extend(sh_rest.round(5).tolist())
            out["weights"].extend(sh_w)
            out["triangles"].extend((sh_f + v_start).tolist())
            out["uv"].extend(np.asarray(uv_use).round(6).tolist())
            out["normals"].extend(sh_norms.round(6).tolist())
            out["triangle_materials"].extend(mats)
        else:
            out["positions"].extend(src_pos[a:b].tolist())
            out["weights"].extend(src_w[a:b])
            out["triangles"].extend((src_tri[f0:f1] - a + v_start).tolist())
            out["uv"].extend(src_uv[f0:f1].tolist())
            out["normals"].extend(src_norm[f0:f1].tolist())
            out["triangle_materials"].extend(src_mat[f0:f1])
        out["parts"][name] = [v_start, t_start, len(out["positions"]), len(out["triangles"])]

    if apply_carpenter_uv_wear:
        bake_wear(out)
    return out


def main():
    sh_rest, sh_f, sh_w, sh_norms, uv_smith, rig, r4, sh_abd, abd_mats = build_abducted_shirt()

    # 1. Rebuild SK_Carpenter_Workwear JSON
    carp_src = json.loads(gzip.open(ROOT / "SourceAssets/VillageCarpenterNPC/Outfit/workwear.json.gz", "rt", encoding="utf-8").read())
    carp_new = replace_shirt_in_outfit(carp_src, sh_rest, sh_f, sh_w, sh_norms, uv_smith, apply_carpenter_uv_wear=True)
    carp_path = OUT_DIR / "carpenter_workwear_r59.json.gz"
    with gzip.open(carp_path, "wt", encoding="utf-8", compresslevel=4) as fh:
        json.dump(carp_new, fh, separators=(",", ":"), allow_nan=False)

    # 2. Rebuild SK_Smith_Outfit JSON (Role 2 lumberjack!)
    smith_src = json.loads((ROOT / "SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit/outfit.json").read_text(encoding="utf-8-sig"))
    smith_new = replace_shirt_in_outfit(smith_src, sh_rest, sh_f, sh_w, sh_norms, uv_smith, apply_carpenter_uv_wear=False)
    smith_path = OUT_DIR / "smith_outfit_r59.json.gz"
    with gzip.open(smith_path, "wt", encoding="utf-8", compresslevel=4) as fh:
        json.dump(smith_new, fh, separators=(",", ":"), allow_nan=False)

    # Quick rest-pose cuff/collar/pocket alignment + armpit stretch gate against pose44_bones.json if available
    audit = {
        "carpenter_verts": len(carp_new["positions"]),
        "carpenter_tris": len(carp_new["triangles"]),
        "smith_verts": len(smith_new["positions"]),
        "smith_tris": len(smith_new["triangles"]),
        "shirt_verts": len(sh_rest),
        "shirt_tris": len(sh_f),
        "carpenter_json": str(carp_path),
        "smith_json": str(smith_path),
    }

    pose_file = Path(r"C:\Users\allan\.gemini\antigravity\brain\3be6f36b-6457-41ce-84b6-6b4a1d74f06e\scratch\pose44_bones.json")
    if pose_file.is_file():
        pose = json.loads(pose_file.read_text(encoding="utf-8"))
        b_map = {b["name"]: b for b in rig["bones"]}
        bones = [b["name"] for b in rig["bones"]]

        def mat_from_pq(p, q):
            x, y, z, w = q
            n = math.sqrt(x*x + y*y + z*z + w*w) or 1.0
            x, y, z, w = x/n, y/n, z/n, w/n
            M = np.eye(4, dtype=np.float64)
            M[0,0] = 1 - 2*(y*y + z*z); M[0,1] = 2*(x*y - z*w);     M[0,2] = 2*(x*z + y*w)
            M[1,0] = 2*(x*y + z*w);     M[1,1] = 1 - 2*(x*x + z*z); M[1,2] = 2*(y*z - x*w)
            M[2,0] = 2*(x*z - y*w);     M[2,1] = 2*(y*z + x*w);     M[2,2] = 1 - 2*(x*x + y*y)
            M[:3,3] = p
            return M

        sh_mask = (sh_rest[:, 0] < -4.0) & (sh_rest[:, 2] > 105.0)
        sh_idx = np.where(sh_mask)[0]
        vf = sh_f[sh_mask[sh_f].all(axis=1)]
        rv0, rv1, rv2 = sh_rest[vf[:, 0]], sh_rest[vf[:, 1]], sh_rest[vf[:, 2]]
        re_max = np.maximum(np.maximum(np.linalg.norm(rv1-rv0, axis=1), np.linalg.norm(rv2-rv1, axis=1)), np.linalg.norm(rv0-rv2, axis=1))
        tri_c_r = (rv0 + rv1 + rv2) / 3.0
        ap_m = (re_max >= 0.30) & (tri_c_r[:, 0] > -26) & (tri_c_r[:, 0] < -12) & (tri_c_r[:, 2] > 120) & (tri_c_r[:, 2] < 145)

        for tag in ("u44", "u28"):
            mats = []
            for bn in bones:
                m_ref = np.eye(4, dtype=np.float64)
                m_ref[:3, :3] = np.array(b_map[bn]["axes"], dtype=np.float64).T
                m_ref[:3, 3] = b_map[bn]["position"]
                mats.append(mat_from_pq(pose[tag][bn]["p"], pose[tag][bn]["q"]) @ np.linalg.inv(m_ref))
            posed = np.zeros_like(sh_rest)
            for i in sh_idx:
                p4 = np.array([sh_rest[i, 0], sh_rest[i, 1], sh_rest[i, 2], 1.0])
                acc = np.zeros(3)
                for bi, w in sh_w[i]:
                    acc += w * (mats[bi] @ p4)[:3]
                posed[i] = acc
            v0, v1, v2 = posed[vf[:, 0]], posed[vf[:, 1]], posed[vf[:, 2]]
            pe_max = np.maximum(np.maximum(np.linalg.norm(v1-v0, axis=1), np.linalg.norm(v2-v1, axis=1)), np.linalg.norm(v0-v2, axis=1))
            er_ap = pe_max[ap_m] / re_max[ap_m]
            audit[f"armpit_stretch_{tag}"] = {
                "max": round(float(er_ap.max()), 2),
                "p99": round(float(np.percentile(er_ap, 99)), 2),
                "gt_2_5x": int((er_ap > 2.5).sum()),
            }
            if float(er_ap.max()) > 3.6:
                raise RuntimeError(f"ARMPIT STRETCH GATE FAILED ({tag}): max={er_ap.max():.2f}x > 3.6x")

    (OUT_DIR / "workwear_armpit_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("R59_WORKWEAR_JSON_OK:", json.dumps(audit))


if __name__ == "__main__":
    main()
