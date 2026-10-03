"""Split ORIGINAL Meshy faces for the OriginalV06 authoring chain.

No visible surface is generated, replaced, repaired or thrown away here. Source
triangle IDs remain stable. Anatomical protection and surface connectivity are
production inputs; this file does not run an engine or acceptance checks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

ROOT = Path("D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001")
OUT = ROOT / "RecoveryOriginalV06" / "regions"
OUT.mkdir(parents=True, exist_ok=True)


def segment_distance(points, a, b):
    a, b = np.asarray(a), np.asarray(b)
    d = b - a
    t = np.clip((points - a) @ d / max(float(d @ d), 1e-12), 0, 1)
    return np.linalg.norm(points - a - t[:, None] * d, axis=1)


def source_joints(p):
    """Use exposed original skin sections, including the true T-pose arms."""
    g = {
        "pelvis": [0., -.105, .039],
        "spine_01": [0., -.062, .033],
        "spine_02": [0., .030, .026],
        "spine_03": [0., .139, .014],
        "spine_04": [0., .266, .008],
        "spine_05": [0., .406, .014],
        "neck_01": [0., .493, .035],
        "neck_02": [0., .561, .074],
        "head": [0., .630, .112],
    }
    sections = []
    for side, s in [("l", 1), ("r", -1)]:
        # Distal sections have no membrane. Their local centre is measured from
        # the original skin rather than copied from the failed older guides.
        samples = []
        for x in [.45, .50, .55, .60, .65, .70, .735, .765]:
            q = p[(np.abs(p[:, 0] - s*x) < .012) &
                  (p[:, 1] > .37) & (p[:, 1] < .505) & (p[:, 2] > -.115)]
            if len(q):
                centre = np.array([s*x, *np.median(q[:, 1:], axis=0)])
                samples.append(centre)
                sections.append({"side": side, "source_x": s*x,
                                 "skin_vertex_count": len(q),
                                 "skin_section_center_source": centre.tolist(),
                                 "skin_section_bounds_source": [q.min(0).tolist(), q.max(0).tolist()]})
        def section_at(x):
            c = min(samples, key=lambda q: abs(abs(q[0])-x)).copy()
            c[0] = s*x
            return c.tolist()
        g.update({
            "clavicle_"+side: [s*.043, .422, -.005],
            "upperarm_"+side: [s*.198, .454, -.035],
            "lowerarm_"+side: section_at(.535),
            "hand_"+side: section_at(.757),
        })
        # Legs are isolated below the cloak and cross-sections supply the real
        # shin and ankle centres. Keep knee and hip guides inside original skin.
        for bone, y, x, z in [("thigh", -.154, .077, .048),
                              ("calf", -.432, .066, -.116),
                              ("foot", -.658, .098, -.039),
                              ("ball", -.721, .115, .058)]:
            q = p[(p[:, 0]*s > .012) & (p[:, 0]*s < .15) &
                  (np.abs(p[:, 1]-y) < .012) & (p[:, 2] > -.17)]
            if len(q) and bone in {"calf", "foot"}:
                med = np.median(q, axis=0)
                x, z = abs(float(med[0])), float(med[2])
            g[bone+"_"+side] = [s*x, y, z]
    return g, sections


def body_protection(p, g):
    x, y, z = p.T
    ax = np.abs(x)
    core = np.zeros(len(p), dtype=bool)
    chain = [("pelvis", "spine_02", .082), ("spine_02", "spine_04", .078),
             ("spine_04", "spine_05", .083), ("spine_05", "neck_01", .075),
             ("neck_01", "neck_02", .069), ("neck_02", "head", .085)]
    for side in ["l", "r"]:
        chain += [("clavicle_"+side, "upperarm_"+side, .052),
                  ("upperarm_"+side, "lowerarm_"+side, .047),
                  ("lowerarm_"+side, "hand_"+side, .047),
                  ("thigh_"+side, "calf_"+side, .042),
                  ("calf_"+side, "foot_"+side, .036),
                  ("foot_"+side, "ball_"+side, .060)]
    for a, b, radius in chain:
        core |= segment_distance(p, g[a], g[b]) < radius
    # These are source-specific geometric separation facts. The outer gills
    # end before abs(X)=.44; everything farther out is an arm/hand, never cloth.
    core |= ax > .44
    core |= (ax > .34) & (y > .411) & (z > -.095)
    core |= (y < -.57)
    core |= (y < -.305) & (ax < .13) & (z > -.165)
    core |= (ax < .135) & (y > -.30) & (y < .485) & (z > -.026)
    core |= (ax < .075) & (y > -.18) & (y < .50)
    core |= (y > .52) & (z > -.015)
    core |= (y > .555) & (ax < .087) & (z > -.13)
    return core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft-components", action="store_true")
    args = ap.parse_args()
    src = np.load(ROOT / "Authoring" / "source_mesh.npz")
    p = src["positions"].astype(np.float64)
    faces = src["indices"].reshape(-1, 3).astype(np.int32)
    normals = src["normals"].astype(np.float64)
    g, sections = source_joints(p)
    quant = np.rint(p / 1e-6).astype(np.int64)
    _, first, inv = np.unique(quant, axis=0, return_index=True, return_inverse=True)
    centres = p[first]
    wc = len(first)
    vn = normals[first]
    wn = np.bincount(inv)
    core = body_protection(p, g)
    # Close the exposed thigh tubes. The original leg surface spreads posterior
    # to the straight hip/knee segment; it is not a membrane simply because it
    # lies beyond a guessed capsule.
    core |= (np.abs(p[:,0]) < .135) & (p[:,1] < -.17) & (p[:,2] > -.125)
    core |= (p[:,1] > .48) & (p[:,2] > .03)
    wb = np.bincount(inv, weights=core) / wn > .5
    wf = inv[faces]
    edges = np.concatenate([wf[:, [0, 1]], wf[:, [1, 2]], wf[:, [2, 0]]])
    edges.sort(axis=1)
    edges = np.unique(edges, axis=0)
    ce = edges[~(wb[edges[:, 0]] | wb[edges[:, 1]])]
    # Do not join left/right gills across the monitoring/spine attachment.
    ce = ce[centres[ce[:, 0], 0] * centres[ce[:, 1], 0] >= 0]
    graph = coo_matrix((np.ones(2*len(ce), np.uint8),
                       (np.r_[ce[:, 0], ce[:, 1]], np.r_[ce[:, 1], ce[:, 0]])),
                      shape=(wc, wc)).tocsr()
    cn, cl = connected_components(graph, directed=False)
    sizes = np.bincount(cl[~wb])
    major = np.argsort(sizes)[-30:][::-1]
    records = []
    for cid in major:
        ids = np.flatnonzero((cl == cid) & ~wb)
        q = centres[ids]
        if len(q):
            records.append({"component": int(cid), "vertices": len(q),
                            "bounds": [q.min(0).tolist(), q.max(0).tolist()],
                            "centroid": q.mean(0).tolist()})
    plan = {"revision": "OriginalV06", "source_transform_to_meters":
            {"axes": ["X", "-Z", "Y-groundY"], "scale": 3.1/(p[:,1].max()-p[:,1].min()),
             "ground_source_y": float(p[:,1].min())},
            "joint_guides_source": g, "source_skin_cross_sections": sections,
            "source_triangle_count": len(faces), "source_vertex_count": len(p),
            "body_protected_vertices": int(core.sum()),
            "source_components_after_anatomical_protection": records,
            "tested": False, "user_accepted": False}
    (OUT/"joint_guides_source.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    if args.draft_components:
        print(json.dumps(records[:15], indent=2), flush=True)
        return
    # Isolated central tissue/fold components remain opaque body. Surface
    # fragments do not acquire a cloth label from proximity to a leaf tip.
    for rec in records:
        qmin, qmax = np.asarray(rec["bounds"])
        if max(abs(qmin[0]), abs(qmax[0])) < .15 or rec["vertices"] < 100:
            wb[cl == rec["component"]] = True
    ce = edges[~(wb[edges[:,0]] | wb[edges[:,1]])]
    ce = ce[centres[ce[:,0],0] * centres[ce[:,1],0] >= 0]
    candidate_ids = np.flatnonzero(~wb)
    candidate_tree = cKDTree(centres[candidate_ids])
    pair_chunks = []
    # The visible source already has front and back membrane surfaces. Pair
    # their closest opposing normal samples in the classification graph only.
    # The retained rendering mesh, UV seams and source positions are untouched.
    for start in range(0, len(candidate_ids), 8192):
        ids = candidate_ids[start:start+8192]
        distances, local = candidate_tree.query(centres[ids], k=48,
                                                distance_upper_bound=.0075,
                                                workers=4)
        good = local < len(candidate_ids)
        safe_local = np.minimum(local, len(candidate_ids)-1)
        target = candidate_ids[safe_local]
        delta = centres[target] - centres[ids,None,:]
        alignment = np.abs(np.einsum("ijk,ik->ij", delta, vn[ids]))
        alignment /= np.maximum(distances, 1e-12)
        opposite = np.einsum("ijk,ik->ij", vn[target], vn[ids]) < -.55
        same_side = centres[target,0] * centres[ids,None,0] >= 0
        good &= opposite & same_side & (alignment > .45) & (distances > 1e-6)
        choices = np.where(good, distances, np.inf)
        which = np.argmin(choices, axis=1)
        have = np.isfinite(choices[np.arange(len(ids)),which])
        if have.any():
            pair_chunks.append(np.c_[ids[have], target[np.arange(len(ids))[have],which[have]]])
    paired = np.concatenate(pair_chunks) if pair_chunks else np.empty((0,2),np.int64)
    paired.sort(axis=1)
    paired = np.unique(paired,axis=0)
    all_ce = np.unique(np.concatenate([ce,paired]),axis=0)
    lengths = np.linalg.norm(centres[all_ce[:,0]]-centres[all_ce[:,1]],axis=1)
    graph = coo_matrix((np.r_[lengths,lengths],
                       (np.r_[all_ce[:,0],all_ce[:,1]],np.r_[all_ce[:,1],all_ce[:,0]])),
                      shape=(wc,wc)).tocsr()
    # These are actual separate source depth/extent patches, not three nearby
    # guesses on the same fringe. The forward patch contains the thin anterior
    # surface; opposite-shell graph links give both sides the same owner.
    seeds, seed_records = [], []
    targets = [(.325,.285,-.213),(.300,-.300,-.112),(.340,.195,-.051)]
    root_targets = [(.102,.635,-.145),(.157,.555,-.104),(.198,.485,-.084)]
    for side, sign in [("l",1),("r",-1)]:
        side_ids = candidate_ids[centres[candidate_ids,0]*sign > .16]
        tree = cKDTree(centres[side_ids])
        for layer, target in enumerate(targets):
            target = np.asarray(target) * np.asarray([sign,1,1])
            _, local = tree.query(target)
            seed = int(side_ids[int(local)])
            seeds.append(seed)
            root_target = np.asarray(root_targets[layer]) * np.asarray([sign,1,1])
            _, root_local = tree.query(root_target)
            root_seed = int(side_ids[int(root_local)])
            seeds.append(root_seed)
            seed_records.append({"id":str(len(seed_records)+1).zfill(2),"side":side,
                                 "layer":layer,"seed_source":centres[seed].tolist(),
                                 "seed_source_vertex_id":int(first[seed]),
                                 "shoulder_seed_source":centres[root_seed].tolist(),
                                 "shoulder_seed_source_vertex_id":int(first[root_seed])})
    distance = dijkstra(graph,directed=False,indices=seeds).reshape(6,2,wc).min(axis=1)
    wlabels = np.argmin(distance,axis=0).astype(np.int8)+1
    wlabels[wb] = 0
    unreached = ~np.isfinite(distance.min(axis=0)) & ~wb
    # Small source detail islands retain the semantic label of their nearest
    # graph-reached sheet on the same side, including opposite surface shells.
    for sign in [1,-1]:
        ids = np.flatnonzero(unreached & (centres[:,0]*sign >= 0))
        reached = np.flatnonzero(~unreached & ~wb & (centres[:,0]*sign >= 0))
        if len(ids) and len(reached):
            _, near = cKDTree(centres[reached]).query(centres[ids],workers=4)
            wlabels[ids] = wlabels[reached[near]]
    vertex_labels = wlabels[inv]
    tri_labels = vertex_labels[faces]
    face_labels = np.zeros(len(faces), np.int8)
    # Attachment triangles touching protected anatomical tissue remain body.
    # This conservative seam protects shoulder/arm continuity and provides a
    # shared fixed border rather than cutting a hole in visible skin.
    body_faces = (tri_labels == 0).any(1)
    votes = np.stack([(tri_labels == i).sum(1) for i in range(1,7)],axis=1)
    face_labels[~body_faces] = (np.argmax(votes[~body_faces],axis=1)+1).astype(np.int8)
    # A face labels the original triangle once. Its original corner coordinates,
    # normals and UVs are recovered by downstream authoring using source IDs.
    arrays = {"face_labels":face_labels,"vertex_labels":vertex_labels,
              "source_face_ids":np.arange(len(faces),dtype=np.int32),
              "source_vertex_ids":np.arange(len(p),dtype=np.int32),
              "source_welded_vertex_ids":inv.astype(np.int32)}
    vertex_incidence = coo_matrix((np.ones(faces.size,np.uint8),
                                  (faces.ravel(),np.repeat(np.arange(len(faces)),3))),
                                 shape=(len(p),len(faces))).tocsr()
    body_vertex_use = np.asarray(vertex_incidence @ body_faces.astype(np.int8)).ravel() > 0
    vertex_labels[body_vertex_use] = 0
    arrays["body_source_vertex_ids"] = np.flatnonzero(body_vertex_use).astype(np.int32)
    panel_records = []
    for label in range(1,7):
        fids = np.flatnonzero(face_labels == label)
        vids = np.unique(faces[fids])
        boundary = vids[body_vertex_use[vids]]
        # UV duplicate borders are paired through the welded source vertex map.
        body_weld = np.zeros(wc,bool)
        body_weld[inv[np.flatnonzero(body_vertex_use)]] = True
        boundary = vids[body_weld[inv[vids]]]
        source_points = p[vids]
        if len(boundary):
            roots = p[boundary]
            shoulder = roots[roots[:,1] >= np.quantile(roots[:,1], .75)]
        else:
            shoulder = source_points[source_points[:,1] >= np.quantile(source_points[:,1],.98)]
        root_target = np.median(shoulder,axis=0)
        root_local = int(np.argmin(np.linalg.norm(source_points-root_target,axis=1)))
        tip_points = source_points[source_points[:,1] <= np.quantile(source_points[:,1],.02)]
        tip_target = np.median(tip_points,axis=0)
        tip_local = int(np.argmin(np.linalg.norm(source_points-tip_target,axis=1)))
        rec = {**seed_records[label-1],"source_triangle_count":len(fids),
               "source_vertex_count":len(vids),
               "root_source":source_points[root_local].tolist(),
               "root_source_vertex_id":int(vids[root_local]),
               "tip_source":source_points[tip_local].tolist(),
               "tip_source_vertex_id":int(vids[tip_local]),
               "body_attachment_source_vertex_count":len(boundary),
               "bounds_source":[source_points.min(0).tolist(),source_points.max(0).tolist()]}
        arrays[f"gill_{label:02d}_attachment_source_vertex_ids"] = boundary.astype(np.int32)
        arrays[f"gill_{label:02d}_source_face_ids"] = fids.astype(np.int32)
        panel_records.append(rec)
    output = OUT / "source_regions_original_v06.npz"
    np.savez_compressed(output,**arrays)
    plan.update({"stage":"original surface body and six membrane regions authored",
                 "method":"source-specific anatomical protection, original triangle adjacency and opposing thin-shell pairing; actual separated depth/extent source patches",
                 "original_surface_replaced":False,"visible_geometry_generated":False,
                 "source_faces_discarded":0,"source_faces_duplicated":0,
                 "source_normal_uv_data_preserved":True,
                 "opposing_shell_graph_pair_count":len(paired),
                 "faces_by_region":{str(i):int((face_labels==i).sum()) for i in range(7)},
                 "membrane_tip_guides":panel_records,
                 "semantic_partition_user_accepted":False,
                 "scale_to_meters":float(3.1/(p[:,1].max()-p[:,1].min())),
                 "ground_source_y":float(p[:,1].min()),
                 "source_regions_file":str(output),
                 "limitations":"The joined Meshy source has fused leaf attachments. Six surface ownership regions are authored candidates; no rendered or runtime acceptance performed. Conservative ambiguous skin remains body."})
    plan["joint_guides_m"] = {name:[float(c[0]*plan["scale_to_meters"]),
                                      float(-c[2]*plan["scale_to_meters"]),
                                      float((c[1]-plan["ground_source_y"])*plan["scale_to_meters"])]
                                for name,c in g.items()}
    (OUT/"joint_guides_source.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    (OUT/"region_authoring_original_v06.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    print(json.dumps({"saved":str(output),"faces":plan["faces_by_region"],
                      "opposing_shell_pairs":len(paired)},indent=2),flush=True)


if __name__ == "__main__":
    main()
