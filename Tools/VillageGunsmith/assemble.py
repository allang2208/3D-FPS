"""Fit the Meshy bust to the R4 neck and provide the full workwear silhouette to the rig solver."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import trimesh

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Tools/VillageBaker"))
from assemble import fit

SRC = PROJECT / "SourceAssets/VillageGunsmith"
OUT = SRC / "Assembly"
SMITH = PROJECT / "SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit"
JASON = PROJECT / "SourceAssets/JasonStrong20261117/R3_ArmsRefined/AnatomyReview"


def add_surface(scene, name, positions, faces, uv, color):
    # The R4 authoring frame faces +Y, whereas the Meshy biped solver faces glTF +Z.
    corners, inverse = np.unique(np.column_stack((faces.ravel(), uv.reshape(-1, 2))),
                                 axis=0, return_inverse=True)
    xyz = positions[corners[:, 0].astype(int)][:, [0, 2, 1]] * [-1., 1., 1.]
    mesh = trimesh.Trimesh(xyz, inverse.reshape(-1, 3), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=corners[:, 1:], material=
        trimesh.visual.material.PBRMaterial(name=name, baseColorTexture=color,
                                             metallicFactor=0., roughnessFactor=.75))
    scene.add_geometry(mesh, geom_name=name, node_name=name)


def main():
    tex = OUT / "Textures"
    tex.mkdir(parents=True, exist_ok=True)
    fit(OUT, glb=SRC / "Meshy/head.glb", texture_dir=tex, prefix="Gunsmith",
        native_skin=SMITH / "Textures/T_Smith_Skin_head_BC.png",
        wardrobe=SMITH / "Smith_Body_Workwear.blend", export_wardrobe=False)
    head = np.load(OUT / "head.npz")
    setup = json.loads((OUT / "setup.json").read_text())
    scene = trimesh.Scene()
    for index, atlas in enumerate(setup["materials"]):
        use = head["m"] == index
        color = Image.open(atlas["BC"]).convert("RGB")
        color.thumbnail((1024, 1024))
        add_surface(scene, "Head_" + str(index), head["p"], head["tri"][use], head["uv"][use], color)
    body = json.loads((JASON / "derived_saved_mesh.json").read_bytes())
    workwear = json.loads((SMITH / "outfit.json").read_bytes())
    for data, label, materials, slots in (
            (body, "Body", [0, 1, 2, 3], ["Skin_body"] * 4),
            (workwear, "Workwear", range(len(workwear["material_slots"])), workwear["material_slots"])):
        positions = np.asarray(data["positions"]) * .01
        triangles = np.asarray(data["triangles"])[:, ::-1]
        uv = np.asarray(data["triangle_uvs" if label == "Body" else "uv"])[:, ::-1].copy()
        uv[:, :, 1] = 1 - uv[:, :, 1]
        for index in materials:
            use = np.asarray(data["triangle_materials"]) == index
            color = Image.open(SMITH / "Textures" / ("T_Smith_" + slots[index] + "_BC.png")).convert("RGB")
            color.thumbnail((256, 256))
            add_surface(scene, f"{label}_{index}", positions, triangles[use], uv[use], color)
    scene.export(SRC / "Rig/assembled.glb")


if __name__ == "__main__":
    main()
