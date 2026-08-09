#!/usr/bin/env python
"""UniRig 蒙皮权重 → WolfRig 18 骨权重转移（黑狼管线步骤 2/3）。

用法：python tools/transfer_unirig_weights.py <unirig_glb> <out_bin>

原理：UniRig 输出 83 根泛型骨（bone_N，无语义）且层级为长链不可直接动画，
但逐顶点权重是空间自洽的。本脚本把权重转移到 scripts/wolf_rig.gd 的 18 骨手工骨架：
  1. 每根 UniRig 骨求影响质心（模型空间），归到最近的骨骼线段 → 六条链之一
     （脊柱/尾/前左/前右/后左/后右）——UniRig 提供区域分割，杜绝跨身体拉扯；
  2. 顶点取其主导 UniRig 骨的链归属，在链内按顶点到各线段的逆平方距离出平滑权重。
输出 bin：[u32 顶点数][u32 每顶点影响数=4] + int32 bones[n*4] + float32 weights[n*4]，
供 tools/bake_wolf_rig.gd（WEIGHTS_BIN）消费。顶点序与 unirig_glb 网格一致。
"""
import json
import struct
import sys

import numpy as np

# 与 scripts/wolf_rig.gd BONE_DEFS / SKIN_SEGS 保持一致（2026-08-09 按 CuMesh 版新狼重新实测）
BONES = [
    ("pelvis", (0, 0.136, -0.22)), ("spineMid", (0, 0.138, -0.05)), ("chest", (0, 0.124, 0.10)),
    ("neck", (0, 0.160, 0.24)), ("head", (0, 0.136, 0.40)), ("tail", (0, 0.0, -0.35)),
    ("FLRoot", (-0.082, -0.010, 0.177)), ("FLKnee", (-0.080, -0.12, 0.21)), ("FLPaw", (-0.078, -0.227, 0.240)),
    ("FRRoot", (0.082, -0.005, 0.175)), ("FRKnee", (0.087, -0.11, 0.185)), ("FRPaw", (0.091, -0.227, 0.195)),
    ("HLRoot", (-0.082, -0.012, -0.190)), ("HLKnee", (-0.094, -0.12, -0.21)), ("HLPaw", (-0.106, -0.226, -0.230)),
    ("HRRoot", (0.082, -0.011, -0.184)), ("HRKnee", (0.095, -0.12, -0.21)), ("HRPaw", (0.107, -0.226, -0.233)),
]
# 链：脊柱 / 尾 / FL / FR / HL / HR；段 [a, b, 目标骨骼下标]
CHAINS = [
    [(0, 1, 0), (1, 2, 1), (2, 3, 2), (3, 4, 4)],
    [(0, 5, 5)],
    [(6, 7, 6), (7, 8, 7)],
    [(9, 10, 9), (10, 11, 10)],
    [(12, 13, 12), (13, 14, 13)],
    [(15, 16, 15), (16, 17, 16)],
]
ALL_SEGS = [s for c in CHAINS for s in c]
SEG2CHAIN = {s: ci for ci, c in enumerate(CHAINS) for s in c}
BP = np.array([b[1] for b in BONES])


def seg_d2(a, b, p):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    p = np.asarray(p, float)
    ab = b - a
    ap = p - a
    l2 = ab @ ab
    t = np.clip(ap @ ab / l2, 0, 1) if l2 > 1e-12 else np.zeros(p.shape[:-1])
    q = a + ab * np.expand_dims(t, -1)
    return ((p - q) ** 2).sum(-1)


def load_glb(path):
    with open(path, "rb") as f:
        struct.unpack("<III", f.read(12))
        clen, _ = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(clen))
        blen, _ = struct.unpack("<II", f.read(8))
        buf = f.read(blen)

    def acc_data(ai):
        acc = js["accessors"][ai]
        bv = js["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
        dt = {5126: "<f4", 5123: "<u2", 5125: "<u4", 5121: "<u1"}[acc["componentType"]]
        return np.frombuffer(buf, dtype=dt, count=acc["count"] * ncomp, offset=off).reshape(acc["count"], ncomp)

    prim = js["meshes"][0]["primitives"][0]
    pos = acc_data(prim["attributes"]["POSITION"]).astype(np.float64)
    joints = acc_data(prim["attributes"]["JOINTS_0"]).astype(np.int64)
    weights = acc_data(prim["attributes"]["WEIGHTS_0"]).astype(np.float64)
    nbones = len(js["skins"][0]["joints"])
    return pos, joints, weights, nbones


def main(glb_path, out_path):
    pos, J, W, nbones = load_glb(glb_path)
    n = pos.shape[0]

    # 每根 UniRig 骨的影响质心（模型空间）
    S = np.zeros(nbones)
    C = np.zeros((nbones, 3))
    for k in range(4):
        np.add.at(S, J[:, k], W[:, k])
        np.add.at(C, J[:, k], W[:, k, None] * pos)
    cent = C / np.maximum(S, 1e-9)[:, None]

    # UniRig 骨 → 最近段 → 链
    bone_chain = np.full(nbones, -1)
    for j in range(nbones):
        if S[j] < 1:
            continue
        d2s = np.array([seg_d2(BP[a], BP[b], cent[j]) for a, b, _ in ALL_SEGS])
        bone_chain[j] = SEG2CHAIN[ALL_SEGS[int(np.argmin(d2s))]]

    # 顶点主导骨 → 链
    dom = J[np.arange(n), np.argmax(W, axis=1)]
    vchain = bone_chain[dom]

    EPS = 5e-4
    outJ = np.zeros((n, 4), dtype=np.int64)
    outW = np.zeros((n, 4))
    for ci, segs in enumerate(CHAINS):
        mask = vchain == ci
        if not mask.any():
            continue
        P = pos[mask]
        d2 = np.stack([seg_d2(BP[a], BP[b], P) for a, b, _ in segs], axis=1)
        w = 1.0 / (d2 + EPS)
        k = min(4, len(segs))
        top = np.argsort(-w, axis=1)[:, :k]
        tw = np.take_along_axis(w, top, axis=1)
        tw /= tw.sum(1, keepdims=True)
        tb = np.array([s[2] for s in segs])[top]
        outJ[mask, :k] = tb
        outW[mask, :k] = tw

    miss = vchain < 0
    if miss.any():  # 兜底：全局最近段
        P = pos[miss]
        d2 = np.stack([seg_d2(BP[a], BP[b], P) for a, b, _ in ALL_SEGS], axis=1)
        bi = np.argmin(d2, axis=1)
        outJ[miss] = np.array([[ALL_SEGS[i][2], 0, 0, 0] for i in bi])
        outW[miss] = [1, 0, 0, 0]

    tot = np.zeros(18)
    for k in range(4):
        np.add.at(tot, outJ[:, k], outW[:, k])
    for i, (name, _) in enumerate(BONES):
        print(f"  {name:9s} {tot[i]:10.0f}")
    print("miss:", int(miss.sum()))

    with open(out_path, "wb") as f:
        f.write(struct.pack("<II", n, 4))
        f.write(outJ.astype("<i4").tobytes())
        f.write(outW.astype("<f4").tobytes())
    print("written:", out_path, "verts:", n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
