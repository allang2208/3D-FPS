"""Fit the approved textured Meshy head to the original Jason StrongTall R4 collar."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import trimesh


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / "Tools/VillageBlacksmithNPC/HeadHair"))
from prepare_head import crop, interpolate, ring, unit

sys.path.insert(0, str(PROJECT / "Tools/VillageCarpenterNPC/Head"))
from fit_head import bridge_faces

BAKER = PROJECT / "SourceAssets/VillageBaker"
GLB = BAKER / "HeadR1/Meshy/head.glb"
WARDROBE = BAKER / "WardrobeR1/Baker_Body.blend"
OUT = BAKER / "AssemblyR1"
TEX = OUT / "Textures"
JASON = PROJECT / "SourceAssets/JasonStrong20261117"
WARDROBE_TEX = WARDROBE.parent / "Textures"
NATIVE_SKIN = WARDROBE_TEX / "T_Baker_NativeNeck_BC.png"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_surface(glb=GLB, texture_dir=TEX, prefix="Baker"):
    scene = trimesh.load_scene(glb, process=False, merge_primitives=False)
    # glTF +Z is forward and +Y is up. Jason faces Blender +Y. Use a rotation
    # so the asymmetry in the eyes, mouth and temples stays on the same side.
    axes = np.array([[-1., 0., 0.], [0., 0., 1.], [0., 1., 0.]])
    positions, normals, mappings, triangles, atlases = [], [], [], [], []
    offset = 0
    for node in scene.graph.nodes_geometry:
        matrix, geom = scene.graph[node]
        mesh = scene.geometry[geom]
        if mesh.visual.uv is None:
            raise RuntimeError(f"Missing UV map on Meshy component {geom}")
        material = mesh.visual.material
        atlas = len(atlases)
        maps = {}
        def store(channel, image):
            if image is not None:
                path = texture_dir / f"T_{prefix}_Head_{atlas}_{channel}.png"
                image.save(path)
                maps[channel] = str(path)
        store("BC", material.baseColorTexture)
        store("N", material.normalTexture)
        if material.metallicRoughnessTexture is not None:
            rgb = material.metallicRoughnessTexture.convert("RGB")
            store("R", rgb.getchannel("G"))
            store("M", rgb.getchannel("B"))
        if "BC" not in maps:
            raise RuntimeError(f"No base color atlas on Meshy component {geom}")
        atlases.append(maps)
        transform = axes @ matrix[:3, :3]
        p = mesh.vertices @ transform.T + axes @ matrix[:3, 3]
        n = unit(mesh.vertex_normals @ np.linalg.inv(transform))
        uv = mesh.visual.uv.copy()
        uv[:, 1] = 1 - uv[:, 1]
        positions.append(p)
        normals.append(n)
        mappings.append(np.column_stack([uv, np.full(len(p), atlas)]))
        # The inherited neck clipping and native skin faces use clockwise winding.
        f = mesh.faces[:, ::-1] if np.linalg.det(transform) > 0 else mesh.faces
        triangles.append(f + offset)
        offset += len(p)
    return np.vstack(positions), np.vstack(normals), np.vstack(mappings), np.vstack(triangles), atlases


def original_collar(cut):
    source = load_json(JASON / "R3_ArmsRefined/head_source.json")
    dst = load_json(JASON / "R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json")
    bones = [b["name"] for b in dst["bones"]]
    redirect = []
    for bone in source["bones"]:
        while bone["name"] not in bones:
            bone = source["bones"][bone["parent"]]
        redirect.append(bones.index(bone["name"]))
    weights = []
    for row in source["weights"]:
        values = {}
        for i, w in row:
            j = redirect[i]
            values[j] = values.get(j, 0) + w
        weights.append(values)
    p = np.asarray(source["positions"]) + [0., 0., 4.5]
    skin = np.asarray(source["triangle_materials"]) == 0
    tri = np.asarray(source["triangles"])[skin]
    a, b, c = p[tri].transpose(1, 0, 2)
    tn = np.cross(c - a, b - a)
    n = np.zeros_like(p)
    for col in tri.T:
        np.add.at(n, col, tn)
    n = unit(n)
    corners = np.column_stack([tri.ravel(), np.asarray(source["triangle_uvs"])[skin].reshape(-1, 2)])
    unique, remap = np.unique(corners, axis=0, return_inverse=True)
    ix = unique[:, 0].astype(int)
    collar = crop(p[ix], n[ix], unique[:, 1:], [weights[i] for i in ix], remap.reshape(-1, 3), cut, False)
    return collar, p, weights, bones, dst["skeleton"]


def points_of_fit(p):
    crown = p[:, 2].max()
    span = np.ptp(p[:, 2])
    # Ignore the shoulder ends and the flat undersurface of the photographed bust.
    upper = p[(p[:, 2] > crown - .34 * span) & (p[:, 2] < crown - .12 * span)]
    left, right = np.percentile(upper[:, 0], (1, 99))
    breadth = right - left
    mid = (left + right) * .5
    central = p[(np.abs(p[:, 0] - mid) < .09 * breadth)
                & (p[:, 2] > crown - 1.24 * breadth)
                & (p[:, 2] < crown - .66 * breadth)]
    nose = central[np.argmax(central[:, 1])]
    return crown, nose


def linear_srgb(c):
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)


def color_at(im, uv):
    x = np.clip((uv[:, 0] * im.shape[1]).astype(int), 0, im.shape[1] - 1)
    y = np.clip((uv[:, 1] * im.shape[0]).astype(int), 0, im.shape[0] - 1)
    return im[y, x, :3]


def collar_albedo(atlases, atlas_uv, collar_uv, p, uv, faces, cut, texture_dir=TEX,
                  prefix="Baker", native_skin=NATIVE_SKIN):
    source = np.asarray(Image.open(native_skin).convert("RGB"))
    samples = []
    for i, mat in enumerate(atlases):
        local = atlas_uv[np.rint(atlas_uv[:, 2]).astype(int) == i]
        if len(local):
            samples.extend(color_at(np.asarray(Image.open(mat["BC"]).convert("RGB")), local))
    face_color = linear_srgb(np.median(samples, axis=0) / 255)
    neck_color = linear_srgb(np.median(color_at(source, collar_uv), axis=0) / 255)
    ratio = np.clip(face_color / np.maximum(neck_color, .005), .4, 2.8)
    # Bake the same smooth colour transition for Blender and interchange materials.
    mask = np.zeros((1024, 1024), np.uint8)
    for coords, z in zip(uv[faces], p[faces, 2].mean(axis=1)):
        t = np.clip((z - (cut - 4.8)) / 4.65, 0, 1)
        cv2.fillConvexPoly(mask, np.round(coords * 1023).astype(np.int32), int(255 * t * t * (3 - 2*t)))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    mask = cv2.resize(cv2.GaussianBlur(mask, (5, 5), 0), source.shape[1::-1], interpolation=cv2.INTER_LINEAR)
    tint = source.copy()
    for y in range(0, len(source), 128):
        sl = slice(y, y + 128)
        rgb = linear_srgb(source[sl].astype(np.float32) / 255)
        rgb *= 1 + (ratio - 1) * (mask[sl, :, None].astype(np.float32) / 255)
        srgb = np.where(rgb <= .0031308, 12.92 * rgb, 1.055 * np.power(rgb, 1 / 2.4) - .055)
        tint[sl] = np.round(np.clip(srgb, 0, 1) * 255).astype(np.uint8)
    path = texture_dir / f"T_{prefix}_Neck_BC.png"
    Image.fromarray(tint).save(path)
    maps = {"BC": str(path), "N": str(WARDROBE_TEX / "T_Baker_NativeNeck_N.png")}
    rough = texture_dir / f"T_{prefix}_Neck_R.png"
    with Image.open(WARDROBE_TEX / "T_Baker_NativeNeck_ORM.png") as image:
        image.getchannel("G").save(rough)
    maps["R"] = str(rough)
    return maps, ratio.tolist()


def fit(work, *, glb=GLB, texture_dir=TEX, prefix="Baker", native_skin=NATIVE_SKIN,
        wardrobe=WARDROBE, export_wardrobe=True):
    p, n, u, tri, atlases = source_surface(glb, texture_dir, prefix)
    crown, nose = points_of_fit(p)
    scale = (181.0 - 164.9) / (crown - nose[2])
    p = (p - nose) * scale + [0., 13.2, 164.9]
    cut = max(154.95, float(p[:, 2].min()) + .65)
    if cut > 159:
        raise ValueError(f"The supplied head ends above the neck at {cut:.2f} cm")
    lower_z = cut - .23
    (lp, ln, lu, lw, lf, le), native, native_weights, bones, skeleton = original_collar(lower_z)
    center = np.median(lp[le], axis=0)
    la, li = ring(lp, le, center)
    nearest = cKDTree(native).query(p)[1]
    skull = bones.index("head")
    weights = [native_weights[j] if z < 161.3 else {skull: 1.} for j, z in zip(nearest, p[:, 2])]
    hp, hn, hu, hw, hf, he = crop(p, n, u, weights, tri, cut, True)
    ha, hi = ring(hp, he, center)
    angle = np.arctan2(hp[:, 1] - center[1], hp[:, 0] - center[0])
    target = np.column_stack([np.interp(angle, la, lp[li, ax], period=math.tau) for ax in (0, 1)])
    fade = np.clip((cut + 2.2 - hp[:, 2]) / 2.2, 0, 1)
    fade = fade * fade * (3 - 2 * fade)
    hp[:, :2] += fade[:, None] * (target - hp[:, :2])
    tree = cKDTree(lp[li, :2])
    moved = np.flatnonzero(fade > 0)
    for ix, nx in zip(moved, li[tree.query(hp[moved, :2])[1]]):
        hw[ix] = interpolate(hw[ix], lw[nx], fade[ix])
        hn[ix] = unit(hn[ix] * (1 - fade[ix]) + ln[nx] * fade[ix])
    bridge = bridge_faces(hp[hi], lp[li], ha, la)
    bridge_indices = np.concatenate((hi, li + len(hp)))[bridge]
    bridge_uv = np.vstack((lu[li[tree.query(hp[hi, :2])[1]]], lu[li]))[bridge]
    neck_atlas, ratio = collar_albedo(atlases, hu[hi], lu[li], lp, lu, lf, lower_z,
                                      texture_dir, prefix, native_skin)
    face_material = np.rint(hu[hf[:, 0], 2]).astype(np.int32)
    all_mat = np.concatenate([face_material, np.full(len(lf) + len(bridge), len(atlases), np.int32)])
    atlases.append(neck_atlas)
    # The bridge uses each original ring's vertex indices; material-specific UV
    # seams are stored per corner without cutting the physical neck seam.
    faces = np.vstack([hf, lf + len(hp), bridge_indices])[:, ::-1].copy()
    uvs = np.concatenate((hu[hf, :2], lu[lf], bridge_uv))[:, ::-1].copy()
    uvs[:, :, 1] = 1 - uvs[:, :, 1]
    weights = hw + lw
    joints = np.full((len(weights), 8), -1, np.int16)
    amounts = np.zeros((len(weights), 8), np.float32)
    for i, row in enumerate(weights):
        picked = sorted(row.items(), key=lambda pair: -pair[1])[:8]
        total = sum(weight for _, weight in picked)
        for j, (index, weight) in enumerate(picked):
            joints[i, j], amounts[i, j] = index, weight / total
    np.savez(work / "head.npz", p=np.vstack((hp, lp)) * .01, n=np.vstack((hn, ln)), tri=faces,
             uv=uvs, m=all_mat, joints=joints, weights=amounts)
    record = {"source_head": str(glb.relative_to(PROJECT)), "source_triangles": len(tri),
              "native_body": str(wardrobe.relative_to(PROJECT)), "native_skeleton": skeleton,
              "scale_to_cm": float(scale), "source_nose": nose.tolist(), "nose_cm": [0.,13.2,164.9],
              "crown_cm": 181., "neck_transition_cm": [lower_z, cut, cut+2.2],
              "native_neck_upper_tint_linear": ratio, "face_and_hair_triangles": len(hf),
              "collar_triangles": len(lf), "connecting_triangles": len(bridge)}
    interchange_maps = {}
    for folder in ((WARDROBE_TEX, BAKER / "CapR1") if export_wardrobe else ()):
        for packed in folder.glob("*_ORM.png"):
            with Image.open(packed) as source:
                rough = TEX / (packed.stem[:-4] + "_R.png")
                source.getchannel("G").save(rough)
                metal = source.getchannel("B")
                lo, hi = metal.getextrema()
                mapping = {"rough": str(rough), "metal": lo / 255.}
                if lo != hi:
                    metal_path = TEX / (packed.stem[:-4] + "_M.png")
                    metal.save(metal_path)
                    mapping["metal"] = str(metal_path)
                interchange_maps[packed.name] = mapping
    (work / "setup.json").write_text(json.dumps({"bones": bones, "materials": atlases, "fit": record,
                                                  "fbx_maps": interchange_maps}))


def main():
    TEX.mkdir(parents=True, exist_ok=True)
    blender = os.environ.get("BLENDER_EXE", "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
    with TemporaryDirectory(prefix="baker-assembly-") as tmp:
        work = Path(tmp)
        fit(work)
        subprocess.run([blender, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", str(HERE / "assemble_export.py"), "--", str(work)], check=True)


if __name__ == "__main__":
    main()
