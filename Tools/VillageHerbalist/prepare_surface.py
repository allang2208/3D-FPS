"""Extract the generated character's original PBR atlases for UE import."""
import io
import json
import struct
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
BODY = ROOT / "SourceAssets/VillageHerbalist/FullBody"
OUT = BODY / "UEAuthoringR1"


def glb_chunks(path):
    with path.open("rb") as stream:
        magic, version, _ = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2:
            raise ValueError(f"Expected glTF 2.0 at {path}")
        size, _ = struct.unpack("<II", stream.read(8))
        scene = json.loads(stream.read(size))
        size, _ = struct.unpack("<II", stream.read(8))
        return scene, stream.read(size)


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    source = BODY / "MeshyR1/model.glb"
    scene, blob = glb_chunks(source)
    texture_dir = BODY / "MeshyR1"
    external = {p.stem.lower(): p for p in texture_dir.rglob("*.png")}

    def image_from_texture(texture):
        image = scene["images"][scene["textures"][texture["index"]]["source"]]
        view = scene["bufferViews"][image["bufferView"]]
        offset = view.get("byteOffset", 0)
        return Image.open(io.BytesIO(blob[offset:offset + view["byteLength"]]))

    manifest = []
    for index, material in enumerate(scene["materials"]):
        pbr = material.get("pbrMetallicRoughness", {})
        suffix = "" if len(scene["materials"]) == 1 else f"_{index}"
        prefix = "T_VillageHerbalist" + suffix

        def supplied(role):
            return external.get(f"m{index}_{role}") or (
                external.get(role) if len(scene["materials"]) == 1 else None)

        def surface_image(role, reference):
            supplied_file = supplied(role)
            return Image.open(supplied_file) if supplied_file else image_from_texture(reference)

        files = {}
        for role, channel, texture in [("Color", "base_color", pbr.get("baseColorTexture")),
                                      ("Normal", "normal", material.get("normalTexture"))]:
            if texture or supplied(channel):
                picture = surface_image(channel, texture)
                dest = OUT / f"{prefix}_{role}.png"
                picture.save(dest)
                files[role] = dest.name

        mr = pbr.get("metallicRoughnessTexture")
        packed = image_from_texture(mr).convert("RGB") if mr else None
        roughness = supplied("roughness")
        metallic = supplied("metallic")
        rough = Image.open(roughness).convert("L") if roughness else packed.getchannel("G") if packed else None
        metal = Image.open(metallic).convert("L") if metallic else packed.getchannel("B") if packed else None
        ao = material.get("occlusionTexture")
        if ao or rough or metal:
            occlusion = image_from_texture(ao).convert("RGB").getchannel("R") if ao else None
            channels = [occlusion, rough, metal]
            size = max((im.size for im in channels if im), key=lambda s: s[0] * s[1])
            channels = [im.resize(size, Image.Resampling.LANCZOS) if im else Image.new("L", size, 255)
                        for im in channels]
            dest = OUT / f"{prefix}_ORM.png"
            Image.merge("RGB", channels).save(dest)
            files["ORM"] = dest.name

        manifest.append(dict(source_name=material.get("name", f"Material_{index}"), index=index,
                             name="M_VillageHerbalist" + suffix, files=files,
                             two_sided=material.get("doubleSided", False),
                             alpha=material.get("alphaMode", "OPAQUE"),
                             cutoff=material.get("alphaCutoff", 0.5),
                             color=pbr.get("baseColorFactor", [1, 1, 1, 1]),
                             rough=pbr.get("roughnessFactor", 1.), metal=pbr.get("metallicFactor", 1.),
                             has_occlusion=bool(ao)))
    (OUT / "surfaces.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare()
