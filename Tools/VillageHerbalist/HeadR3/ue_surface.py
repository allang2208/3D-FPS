"""Prepare the generated head's PBR inputs, keeping its original UV atlas."""
import base64
import io
import json
import shutil
import sys
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from prepare_surface import glb_chunks


def prepare(directory):
    source = directory / "Meshy/head.glb"
    out = directory / "UE/Textures"
    out.mkdir(parents=True, exist_ok=True)
    gltf, blob = glb_chunks(source)
    mats = gltf.get("materials", [])
    used = sorted({p.get("material", 0) for m in gltf["meshes"] for p in m["primitives"]})
    external = {p.stem.lower(): p for p in source.parent.rglob("*.png")}

    def read_image(reference):
        tex = gltf["textures"][reference["index"]]
        img = gltf["images"][tex["source"]]
        if "bufferView" in img:
            view = gltf["bufferViews"][img["bufferView"]]
            start = view.get("byteOffset", 0)
            return Image.open(io.BytesIO(blob[start:start + view["byteLength"]]))
        uri = img["uri"]
        if uri.startswith("data:"):
            return Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
        return Image.open(source.parent / uri)

    surfaces = {}
    for order, index in enumerate(used):
        mat = mats[index]
        pbr = mat.get("pbrMetallicRoughness", {})
        suffix = "" if order == 0 else "_" + str(order)
        name = "M_LinZhiHead" + suffix
        stem = "T_LinZhiHead" + suffix
        files = {}

        def explicit(role):
            paths = [f"m{index}_{role}"]
            if len(used) == 1:
                paths.extend((role, f"head_{role}"))
            return next((Image.open(external[k]) for k in paths if k in external), None)

        def image_or_external(role, info):
            external_image = explicit(role)
            return external_image if external_image is not None else read_image(info) if info else None

        def write_image(role, image):
            path = out / (stem + "_" + role + ".png")
            image.save(path)
            files[role] = path.name

        color = image_or_external("base_color", pbr.get("baseColorTexture"))
        if color is None:
            raise ValueError("Missing generated head color atlas for " + name)
        fitted_color = directory / "Assembly/Materials" / (stem + "_Color.png")
        if fitted_color.is_file():
            color = Image.open(fitted_color)
        write_image("Color", color)
        normal = image_or_external("normal", mat.get("normalTexture"))
        if normal:
            write_image("Normal", normal.convert("RGB"))
        mr = pbr.get("metallicRoughnessTexture")
        rough, metal = explicit("roughness"), explicit("metallic")
        if mr and (rough is None or metal is None):
            packed = read_image(mr).convert("RGB")
            rough = rough if rough is not None else packed.getchannel("G")
            metal = metal if metal is not None else packed.getchannel("B")
        ao = image_or_external("occlusion", mat.get("occlusionTexture"))
        if any((ao, rough, metal)):
            size = max((im.size for im in (ao, rough, metal) if im), key=lambda s: s[0] * s[1])
            channels = [im.convert("RGB").getchannel("R").resize(size, Image.Resampling.LANCZOS)
                        if im else Image.new("L", size, 255) for im in (ao, rough, metal)]
            write_image("ORM", Image.merge("RGB", channels))
        surfaces[name] = dict(files=files, source_material=mat.get("name", ""),
                              color=pbr.get("baseColorFactor", [1, 1, 1, 1]),
                              rough=pbr.get("roughnessFactor", 1.), metal=pbr.get("metallicFactor", 1.),
                              ao=ao is not None, alpha=mat.get("alphaMode", "OPAQUE"),
                              cutoff=mat.get("alphaCutoff", .5), two_sided=mat.get("doubleSided", False))
    frame = directory / "T_LinZhiFrames_Color.png"
    frame_files = {}
    if frame.is_file():
        shutil.copyfile(frame, out / frame.name)
        frame_files["Color"] = frame.name
    surfaces["M_LinZhiFrames"] = dict(files=frame_files,
        color=[1., 1., 1., 1.] if frame_files else [.062, .028, .014, 1.], rough=.29, metal=0.)
    (out.parent / "surfaces.json").write_text(json.dumps(surfaces, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare(Path(sys.argv[1]).resolve())
