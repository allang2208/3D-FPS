"""Seat the carpenter on the smith's R4 neck opening in the original body reference pose."""
import gzip
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree


PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "Tools/VillageBlacksmithNPC/HeadHair"))
from prepare_head import crop, interpolate, ring, sample_linear_color, unit

BASE = PROJECT / "SourceAssets/VillageCarpenterNPC"
OUT = BASE / "Head"
INPUTS = BASE / "Meshy/HeadR1/Source"
JASON = PROJECT / "SourceAssets/JasonStrong20261117/R3_ArmsRefined"
NATIVE_ALBEDO = PROJECT / "SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit/Textures/T_Smith_Skin_head_BC.png"
COLLAR_Z = 154.5
FACE_Z = 154.85
FADE_HEIGHT = 1.85


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def native_neck():
    native = load(JASON / "head_source.json")
    body = load(JASON / "AnatomyReview/derived_saved_mesh.json")
    names = {b["name"]: b["index"] for b in body["bones"]}
    redirect = {}
    for i, bone in enumerate(native["bones"]):
        while bone["name"] not in names:
            bone = native["bones"][bone["parent"]]
        redirect[i] = names[bone["name"]]

    points = np.array(native["positions"]) + [0, 0, 4.5]
    weights = []
    for source in native["weights"]:
        mapped = {}
        for index, amount in source:
            i = redirect[index]
            mapped[i] = mapped.get(i, 0.) + amount
        weights.append(mapped)
    skin = np.asarray(native["triangle_materials"]) == 0
    faces = np.array(native["triangles"])[skin]
    ns = np.zeros_like(points)
    a, b, c = points[faces].transpose(1, 0, 2)
    tri_normals = np.cross(c - a, b - a)
    for col in faces.T:
        np.add.at(ns, col, tri_normals)
    ns = unit(ns)
    corners = np.column_stack((faces.ravel(), np.array(native["triangle_uvs"])[skin].reshape(-1, 2)))
    unique, indices = np.unique(corners, axis=0, return_inverse=True)
    ids = unique[:, 0].astype(int)
    collar = crop(points[ids], ns[ids], unique[:, 1:], [weights[i] for i in ids],
                  indices.reshape(-1, 3), COLLAR_Z, False)
    return collar, points, weights, names["head"], body["skeleton"]


def bridge_faces(upper, lower, angles_upper, angles_lower):
    nu, nl = len(upper), len(lower)
    vertices = np.vstack((upper, lower))
    axis = lower[:, :2].mean(axis=0)
    i = j = 0
    faces = []
    while i < nu or j < nl:
        au = angles_upper[(i + 1) % nu] + (math.tau if i + 1 >= nu else 0)
        al = angles_lower[(j + 1) % nl] + (math.tau if j + 1 >= nl else 0)
        if i < nu and (j >= nl or au < al):
            tri = [i % nu, (i + 1) % nu, nu + j % nl]
            i += 1
        else:
            tri = [i % nu, nu + (j + 1) % nl, nu + j % nl]
            j += 1
        a, b, c = vertices[tri]
        outward = vertices[tri, :2].mean(axis=0) - axis
        if np.dot(np.cross(b - a, c - a)[:2], outward) > 0:
            tri.reverse()
        faces.append(tri)
    return np.array(faces)


def make_masks():
    rough = Image.open(INPUTS / "texture_0_roughness.png").convert("L")
    metal = Image.open(INPUTS / "texture_0_metallic.png").convert("L")
    color = np.asarray(Image.open(INPUTS / "texture_0_base_color.png").convert("RGB")
                       .resize(rough.size, Image.Resampling.LANCZOS), dtype=np.float32)
    # Warm, bright skin receives scattering; baked dark hair stays opaque.
    chroma = color[:, :, 0] - color[:, :, 2]
    skin = np.clip((chroma - 13) / 23, 0, 1) * np.clip((color[:, :, 0] - 58) / 55, 0, 1)
    sss = Image.fromarray(np.uint8(np.round(skin * 255)))
    Image.merge("RGB", (sss, rough, metal)).save(OUT / "T_Carpenter_Head_SRM.png")


def split_overfull_edges(points, faces, materials):
    # The game mesh builder accepts at most two faces per indexed edge. Remove coincident
    # duplicate triangles and keep each additional surface sheet on its own indexed corners.
    corners = points[faces]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    _, unique = np.unique(np.sort(faces, axis=1), axis=0, return_index=True)
    keep = np.sort(unique[area[unique] > 1e-9])
    triangles = faces[keep].copy()
    edges = {}
    extras = []
    for index, row in enumerate(triangles.tolist()):
        pairs = [tuple(sorted((row[i], row[(i + 1) % 3]))) for i in range(3)]
        if any(edges.get(pair, 0) == 2 for pair in pairs):
            first = len(points) + len(extras)
            extras.extend(row)
            triangles[index] = [first, first + 1, first + 2]
        else:
            for pair in pairs:
                edges[pair] = edges.get(pair, 0) + 1
    remap = np.concatenate((np.arange(len(points)), np.array(extras, dtype=int)))
    return remap, triangles, materials[keep]


def main():
    (lp, ln, luv, lw, lf, lower_edges), native, weights, head_bone, skeleton = native_neck()
    center = np.median(lp[lower_edges], axis=0)
    la, li = ring(lp, lower_edges, center)
    with np.load(OUT / "game_surface.npz") as mesh:
        raw, n, uv, tris = (mesh[k] for k in ("p", "n", "uv", "tri"))
        crown, tip = mesh["crown"].item(), mesh["nose"]
    scale = (181.0 - 164.9) / (crown - tip[2])
    points = (raw - tip) * scale + [0, 13.2, 164.9]
    nearest = cKDTree(native).query(points)[1]
    # Let the shoulder contour move with R4's native neck and keep the hanging hair on the skull.
    w = [weights[idx] if z < 161.5 and (y > -6.0 or z < 156.9) else {head_bone: 1.}
         for idx, (_, y, z) in zip(nearest, points)]
    p, n, uv, w, f, upper_edges = crop(points, n, uv, w, tris, FACE_Z, True)
    ha, hi = ring(p, upper_edges, center)
    theta = np.arctan2(p[:, 1] - center[1], p[:, 0] - center[0])
    target = np.column_stack([np.interp(theta, la, lp[li, ax], period=math.tau) for ax in (0, 1)])
    fade = np.clip((FACE_Z + FADE_HEIGHT - p[:, 2]) / FADE_HEIGHT, 0, 1)
    fade = fade * fade * (3 - 2 * fade)
    p[:, :2] += (target - p[:, :2]) * fade[:, None]
    tree = cKDTree(lp[li, :2])
    moved = np.flatnonzero(fade > 0)
    for k, idx in zip(moved, li[tree.query(p[moved, :2])[1]]):
        w[k] = interpolate(w[k], lw[idx], fade[k])
        n[k] = unit(n[k] * (1 - fade[k]) + ln[idx] * fade[k])
    hmatch = li[tree.query(p[hi, :2])[1]]
    bridge = bridge_faces(p[hi], lp[li], ha, la)
    face_color = sample_linear_color(INPUTS / "texture_0_base_color.png", uv[hi])
    native_color = sample_linear_color(NATIVE_ALBEDO, luv[li])
    tint = np.clip(face_color / np.maximum(native_color, .005), .30, 3.)
    all_points = np.vstack((p, lp, p[hi], lp[li]))
    normals = np.vstack((n, ln, ln[hmatch], ln[li]))
    texture_coords = np.vstack((uv, luv, luv[hmatch], luv[li]))
    faces = np.vstack((f, lf + len(p), bridge + len(p) + len(lp)))
    skin = w + lw + [w[i] for i in hi] + [lw[i] for i in li]
    materials = np.concatenate((np.zeros(len(f), np.int32), np.ones(len(lf) + len(bridge), np.int32)))
    remap, faces, materials = split_overfull_edges(all_points, faces, materials)
    geometry = {"p": all_points[remap].round(6).tolist(), "n": normals[remap].round(7).tolist(),
                "uv": texture_coords[remap].round(7).tolist(), "tri": faces.tolist(),
                "w": [list(skin[i].items()) for i in remap], "m": materials.tolist()}
    with gzip.open(OUT / "fitted.json.gz", "wt", encoding="utf-8", compresslevel=3) as fp:
        json.dump(geometry, fp, separators=(",", ":"))
    make_masks()
    report = {"skeleton": skeleton, "nose_target_cm": [0, 13.2, 164.9], "crown_cm": 181.,
              "source_nose_xyz": tip.tolist(), "uniform_scale_cm": float(scale), "head_bone": head_bone,
              "collar_join_cm": [COLLAR_Z, FACE_Z], "blend_ends_cm": FACE_Z + FADE_HEIGHT,
              "upper_neck_linear_tint": tint.tolist(), "face_triangles": int((materials == 0).sum()),
              "neck_and_join_triangles": int((materials == 1).sum()), "lod0_triangles": len(faces)}
    (OUT / "fit.json").write_text(json.dumps(report, indent=2))
    print(report)


if __name__ == "__main__":
    main()
