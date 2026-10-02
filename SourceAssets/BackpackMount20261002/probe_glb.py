# 解析 GLB 结构：网格/材质/贴图/包围盒（纯 stdlib）
import struct, json, sys

p = r"D:\FPS3D\VaultCache\FabLibrary\Soviet_Military_Backpack___Game-Ready_3D_Asset__Low_Poly_Megascan_-8b846967\glb\russianmilitarybackpack.glb"

with open(p, "rb") as f:
    magic, ver, length = struct.unpack("<III", f.read(12))
    clen, ctype = struct.unpack("<II", f.read(8))
    js = json.loads(f.read(clen))
    bin_off = f.tell()
    blen, btype = struct.unpack("<II", f.read(8))
    print("magic", hex(magic), "ver", ver, "bin", blen)

print("nodes:", [(n.get("name"), n.get("mesh"), n.get("scale"), n.get("rotation"), n.get("translation")) for n in js.get("nodes", [])])
print("scenes:", js.get("scenes"))
for i, m in enumerate(js.get("meshes", [])):
    print("mesh", i, m.get("name"))
    for j, pr in enumerate(m["primitives"]):
        a = js["accessors"][pr["attributes"]["POSITION"]]
        print("  prim", j, "mat", pr.get("material"), "attrs", list(pr["attributes"].keys()),
              "mode", pr.get("mode"), "count", a["count"], "min", a.get("min"), "max", a.get("max"))
print("materials:")
for i, m in enumerate(js.get("materials", [])):
    pbr = m.get("pbrMetallicRoughness", {})
    print(" ", i, m.get("name"),
          "baseTex", pbr.get("baseColorTexture"), "baseFac", pbr.get("baseColorFactor"),
          "metTex", pbr.get("metallicRoughnessTexture"), "met", pbr.get("metallicFactor"), "rough", pbr.get("roughnessFactor"),
          "norm", m.get("normalTexture"), "emis", m.get("emissiveTexture"), "occ", m.get("occlusionTexture"))
print("images:", [(im.get("name"), im.get("mimeType"), im.get("bufferView")) for im in js.get("images", [])])
print("textures:", js.get("textures"))
print("samplers:", js.get("samplers"))
print("bufferViews:", len(js.get("bufferViews", [])), "accessors:", len(js.get("accessors", [])))
