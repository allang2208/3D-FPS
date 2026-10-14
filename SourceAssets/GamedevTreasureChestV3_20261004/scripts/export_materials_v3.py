"""Portable, texture-only PBR fallback for interchange exports.

Call setup_export_materials() AFTER opening the authoritative .blend, immediately
before exporting FBX/GLB.  Do not save this temporary material substitution back
over the authoritative .blend.  Original input PNGs are never modified.

The resulting 3-map material families preserve the broad authored finish but
exclude mesh-dependent component rim/bevel wear.  NormalGL maps are OpenGL/Y+
with the final material normal strength already baked into their pixels.  Use
the original DirectX inputs, or invert green, when an engine expects DirectX.

GLB must export_vertex_color='NONE', export_all_vertex_colors=False: the mesh's
Color attributes contain wear metadata, not albedo vertex colors.  FBX retains
material slots and direct image references; its PBR interpretation is importer-
dependent and is not an Unreal material graph or a validated UE material.

Run with system Python and --prepare-only to regenerate derived PNGs without
Blender.  Within Blender, NumPy is bundled and the supported external Python
fallback supplies Pillow only for deterministic PNG decoding/encoding.
"""

from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = HERE / "input" / "FPSGAME_chest_input_20261004"
DEFAULT_OUTPUT = HERE / "exports" / "Textures"
PHYSICAL_UV = "UV0_Physical"
RECIPE_VERSION = "v2-final-20261004-iron026-gold032"


def prepare_textures(input_root=None, output_root=None):
    """Create lossless derived PNGs; sources remain untouched."""
    import numpy as np
    from PIL import Image

    root = Path(input_root or DEFAULT_INPUT).resolve()
    out = Path(output_root or DEFAULT_OUTPUT).resolve()
    out.mkdir(parents=True, exist_ok=True)
    metals = root / "SourceAssets" / "GamedevTreasureChestDetail20261003" / "Textures"
    woods = root / "ExternalTextures" / "UnrealNormandy"

    def read(path):
        return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0

    def decode_srgb(a):
        return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)

    def encode_srgb(a):
        a = np.clip(a, 0, 1)
        return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1.0 / 2.4) - 0.055)

    def write(name, data, color=False):
        if color:
            data = encode_srgb(data)
        image = np.round(np.clip(data, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(image, "RGB").save(out / name, compress_level=6)

    def normal_gl(a, strength):
        n = a * 2.0 - 1.0
        n[..., 1] *= -1.0  # DirectX Y- to OpenGL Y+.
        n[..., :2] *= strength
        n[..., 2] = 1.0 + (n[..., 2] - 1.0) * strength
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-8)
        return n * 0.5 + 0.5

    families = {}
    for family in ("Iron", "Gold", "Wood"):
        metal = family != "Wood"
        iron = family == "Iron"
        prefix = "T_TreasureDetail_" + family + "_" if metal else "T_WoodSurface_00A_"
        folder = metals if metal else woods
        source_color = read(folder / (prefix + "BaseColor.png"))
        source_packed = read(folder / (prefix + ("ORM.png" if metal else "RHAOM.png")))
        source_normal = read(folder / (prefix + "Normal.png"))
        base = decode_srgb(source_color)
        if metal:
            retention = 0.16 if iron else 0.25
            tint = np.asarray((0.027, 0.032, 0.039) if iron else (0.34, 0.19, 0.061), dtype=np.float32)
            base = tint * (1.0 - retention) + base * retention
            ao = 0.72 + 0.28 * source_packed[..., 0]
            rough = 0.34 + (0.20 if iron else 0.22) * source_packed[..., 1]
            metallic = (0.80 if iron else 0.89) + (0.16 if iron else 0.10) * source_packed[..., 2]
            strength = 0.26 if iron else 0.32
        else:
            base *= np.asarray((0.40, 0.31, 0.24), dtype=np.float32)
            ao = 0.78 + 0.22 * source_packed[..., 2]
            rough = source_packed[..., 0] * 0.52 + 0.82 * 0.48
            metallic = np.zeros_like(rough)
            strength = 0.68
        # AO was multiplied into the original Blender base graph.  Fold it in
        # once here and store neutral R=1 so an importer cannot double it.
        base *= ao[..., None]
        packed = np.stack((np.ones_like(rough), rough, metallic), axis=-1)
        filenames = {"base_color": "T_TreasureV2_" + family + "_BaseColor.png",
                     "orm": "T_TreasureV2_" + family + "_ORM.png",
                     "normal": "T_TreasureV2_" + family + "_NormalGL.png"}
        write(filenames["base_color"], base, color=True)
        write(filenames["orm"], packed)
        write(filenames["normal"], normal_gl(source_normal, strength))
        families[family] = dict(files=filenames, size=[int(base.shape[1]), int(base.shape[0])],
                                normal_strength_baked=strength,
                                roughness_min=float(rough.min()), roughness_max=float(rough.max()),
                                metallic_min=float(metallic.min()), metallic_max=float(metallic.max()))
    manifest = dict(recipe_version=RECIPE_VERSION, families=families,
                    original_images_modified=False,
                    base_color="sRGB encoded; tint/contrast compression and gentle AO baked",
                    orm="Linear/non-color: R=1 (AO already in BaseColor), G=roughness, B=metallic",
                    normal="OpenGL tangent Y+; final normal strength baked; runtime strength 1.0",
                    geometry_dependent_edge_wear="Not baked; authoritative Blender material only",
                    export_vertex_colors="Disabled for glTF; existing Color is wear metadata",
                    portability="Texture-only approximation of broad finish; engine import not validated")
    (out / "texture_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("EXPORT_PBR_TEXTURES_READY", str(out))
    return manifest


def _ensure_textures(root, out):
    manifest_file = out / "texture_manifest.json"
    if manifest_file.is_file():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if manifest.get("recipe_version") == RECIPE_VERSION and all(
                (out / filename).is_file() for f in manifest["families"].values()
                for filename in f["files"].values()):
            return manifest
    try:
        import PIL  # noqa: F401
    except ImportError:
        candidates = [shutil.which("python"), shutil.which("python3"), "/usr/local/bin/python", "/usr/bin/python3"]
        for candidate in dict.fromkeys(candidates):
            if not candidate or not Path(candidate).is_file():
                continue
            check = subprocess.run([candidate, "-c", "import numpy, PIL"], capture_output=True)
            if check.returncode == 0:
                subprocess.run([candidate, str(Path(__file__).resolve()), "--prepare-only",
                                "--input-root", str(root), "--output-root", str(out)], check=True)
                return json.loads(manifest_file.read_text(encoding="utf-8"))
        raise RuntimeError("Prepare export PNGs using a Python with NumPy/Pillow before exporting")
    return prepare_textures(root, out)


def setup_export_materials(input_root=None, output_root=None, pack_images=True):
    """Replace only the in-memory graphs with export-friendly direct PBR nodes.

    Material datablock names and object slot references are unchanged.  This
    function never saves a .blend or changes mesh, UV, color, armature or action
    data.  Return the three material datablocks keyed by semantic name.
    """
    import bpy
    root = Path(input_root or DEFAULT_INPUT).resolve()
    out = Path(output_root or DEFAULT_OUTPUT).resolve()
    manifest = _ensure_textures(root, out)
    result = {}
    for family, name in (("Iron", "Treasure_BlackIron"), ("Gold", "Treasure_AntiqueGold"),
                         ("Wood", "Treasure_Interior")):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        nodes = m.node_tree.nodes
        links = m.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (620, 100)
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.location = (340, 100)
        shader.inputs["IOR"].default_value = 1.5
        shader.inputs["Specular IOR Level"].default_value = 0.30 if family == "Wood" else 0.5
        # These are inactive under the connected PNGs, but give limited FBX
        # importers sensible scalar fallbacks instead of default nonmetal.
        shader.inputs["Metallic"].default_value = 0.0 if family == "Wood" else (0.94 if family == "Iron" else 0.97)
        shader.inputs["Roughness"].default_value = 0.70 if family == "Wood" else 0.45
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        uv = nodes.new("ShaderNodeUVMap")
        uv.uv_map = PHYSICAL_UV
        uv.location = (-620, 120)
        textures = {}
        for i, key in enumerate(("base_color", "orm", "normal")):
            texture = nodes.new("ShaderNodeTexImage")
            texture.label = "Portable " + key
            texture.location = (-380, 390 - i * 360)
            texture.image = bpy.data.images.load(str(out / manifest["families"][family]["files"][key]), check_existing=True)
            texture.image.colorspace_settings.name = "sRGB" if key == "base_color" else "Non-Color"
            texture.extension = "REPEAT"
            if pack_images and not texture.image.packed_file:
                texture.image.pack()
            links.new(uv.outputs["UV"], texture.inputs["Vector"])
            textures[key] = texture
        links.new(textures["base_color"].outputs["Color"], shader.inputs["Base Color"])
        separate = nodes.new("ShaderNodeSeparateColor")
        separate.mode = "RGB"
        separate.location = (-100, 30)
        links.new(textures["orm"].outputs["Color"], separate.inputs["Color"])
        links.new(separate.outputs["Green"], shader.inputs["Roughness"])
        links.new(separate.outputs["Blue"], shader.inputs["Metallic"])
        normal = nodes.new("ShaderNodeNormalMap")
        normal.location = (-100, -330)
        normal.space = "TANGENT"
        normal.uv_map = PHYSICAL_UV
        normal.inputs["Strength"].default_value = 1.0
        links.new(textures["normal"].outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])
        m["ExportMaterialApproximation"] = "Direct texture PBR; mesh-dependent edge wear omitted"
        m["ExportNormalConvention"] = "OpenGL Y+; strength baked into NormalGL pixels"
        result[name] = m
    print("EXPORT_PBR_MATERIALS_READY: 3 semantic slots; 9 derived textures; no shader wear")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.prepare_only:
        prepare_textures(args.input_root, args.output_root)
    else:
        setup_export_materials(args.input_root, args.output_root)
