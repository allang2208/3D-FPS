# 从 Fab GLB 提取背包网格与贴图（纯 stdlib，无第三方依赖）：
#   输出 OBJ（cm、UE Z-up：glTF +X→+X、+Y→+Z、+Z→-Y，翻转手性后反转三角序）
#   + 3 张内嵌 PNG（BaseColor / Normal / MetallicRoughness）
#   + 缩放烘焙：源高约 1.97m → 目标登山包高 56cm
# 用法：python extract_glb.py
import struct, json, os, sys

SRC = r"D:\FPS3D\VaultCache\FabLibrary\Soviet_Military_Backpack___Game-Ready_3D_Asset__Low_Poly_Megascan_-8b846967\glb\russianmilitarybackpack.glb"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\BackpackMount20261002"
TARGET_HEIGHT_CM = 56.0

CT_F32 = 5126
CT_U16 = 5123
CT_U32 = 5125
COMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    with open(path, "rb") as f:
        magic, ver, _ = struct.unpack("<III", f.read(12))
        assert magic == 0x46546C67, "not a GLB"
        jlen, jtype = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(jlen))
        blen, _ = struct.unpack("<II", f.read(8))
        bin_data = f.read(blen)
    return js, bin_data


def accessor_data(js, blob, index):
    acc = js["accessors"][index]
    bv = js["bufferViews"][acc["bufferView"]]
    n = COMP[acc["type"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    ct = acc["componentType"]
    fmt = {CT_F32: "f", CT_U16: "H", CT_U32: "I"}[ct]
    count = acc["count"]
    stride = bv.get("byteStride", 0) or n * struct.calcsize(fmt)
    out = []
    for i in range(count):
        vals = struct.unpack_from("<%d%s" % (n, fmt), blob, off + i * stride)
        out.append(vals if n > 1 else vals[0])
    return out


def extract():
    js, blob = read_glb(SRC)
    prim = js["meshes"][0]["primitives"][0]
    pos = accessor_data(js, blob, prim["attributes"]["POSITION"])
    nrm = accessor_data(js, blob, prim["attributes"]["NORMAL"])
    uv = accessor_data(js, blob, prim["attributes"]["TEXCOORD_0"])
    idx = accessor_data(js, blob, prim["indices"])

    ys = [p[1] for p in pos]
    scale = TARGET_HEIGHT_CM / (max(ys) - min(ys)) / 100.0  # glTF 米 → 目标 cm
    print("source height %.1fm -> scale %.4f" % (max(ys) - min(ys), scale))

    obj_path = os.path.join(OUT, "soviet_backpack.obj")
    with open(obj_path, "w") as w:
        w.write("# soviet military backpack, cm, UE Z-up\n")
        for p in pos:
            x, y, z = p
            w.write("v %.6f %.6f %.6f\n" % (x * scale * 100, -z * scale * 100, y * scale * 100))
        for t in uv:
            w.write("vt %.6f %.6f\n" % (t[0], 1.0 - t[1]))
        for n in nrm:
            x, y, z = n
            w.write("vn %.6f %.6f %.6f\n" % (x, -z, y))
        w.write("g backpack\nusemtl M_SovietBackpack\n")
        for i in range(0, len(idx), 3):
            a, b, c = idx[i] + 1, idx[i + 1] + 1, idx[i + 2] + 1
            w.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % (a, a, a, c, c, c, b, b, b))
    print("OBJ", obj_path)

    names = ["T_SovietBackpack_BaseColor.png", "T_SovietBackpack_Normal.png", "T_SovietBackpack_MR.png"]
    for i, name in enumerate(names):
        im = js["images"][i]
        bv = js["bufferViews"][im["bufferView"]]
        data = blob[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]]
        path = os.path.join(OUT, name)
        with open(path, "wb") as w:
            w.write(data)
        print("PNG", name, len(data), "bytes")


if __name__ == "__main__":
    extract()
