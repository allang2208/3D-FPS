# Analysis for a semantic re-split: per connected component and per UV island,
# report z-range, face count and metallic/basecolor stats, plus fine z-bands
# around the old cut, so we can separate head metal from rope collar and stick.
import bpy
import bmesh
import json
import sys
import numpy as np

HERE = 'D:/FPS3D/FPSGAME/SourceAssets/ToolEnhance20260925'
OUT = HERE + '/resplit-analysis.json'

AXE_SRC = 'D:/FPS3D/FPSGAME/SourceAssets/BattleAxeReplace20260919/Fitted/BattleAxe_16000.fbx'
PICK_SRC = 'D:/FPS3D/FPSGAME/SourceAssets/RusticPickaxe20260919/Export/RusticPickaxe_World.fbx'
AXE_METAL = 'D:/FPS3D/FPSGAME/SourceAssets/BattleAxeReplace20260919/Input/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_metallic.png'
AXE_BASE = 'D:/FPS3D/FPSGAME/SourceAssets/BattleAxeReplace20260919/Input/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx/Meshy_AI_Weathered_Battle_Axe_0918025738_texture.png'
PICK_METAL = 'D:/FPS3D/FPSGAME/SourceAssets/RusticPickaxe20260919/Textures/MetallicRoughness.jpg'
PICK_BASE = 'D:/FPS3D/FPSGAME/SourceAssets/RusticPickaxe20260919/Textures/BaseColor.jpg'

TOOLS = {
    'axe': {'src': AXE_SRC, 'metal': AXE_METAL, 'base': AXE_BASE, 'channel': 0,
            'bands': (0.10, 0.35, 0.01)},
    'pickaxe': {'src': PICK_SRC, 'metal': PICK_METAL, 'base': PICK_BASE, 'channel': 2,
                'bands': (0.24, 0.46, 0.01)},
}


def load_raw(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = int(img.size[0]), int(img.size[1])
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return img, np.flipud(buf.reshape(h, w, 4)), w, h


def sample(buf, w, h, uv):
    u = np.clip(uv[:, 0], 0., 1.)
    v = np.clip(uv[:, 1], 0., 1.)
    x = np.minimum((u * (w - 1)).astype(np.int64), w - 1)
    y = np.minimum(((1.0 - v) * (h - 1)).astype(np.int64), h - 1)
    return buf[y, x, 0:3].astype(np.float64)


def face_uv_centroids(me):
    uv = me.uv_layers.active.data
    out = np.empty((len(me.polygons), 2), dtype=np.float64)
    for p in me.polygons:
        acc = np.zeros(2)
        for li in p.loop_indices:
            acc += uv[li].uv
        out[p.index] = acc / max(1, len(p.loop_indices))
    return out


def face_adjacency(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    adj = [[] for _ in range(len(bm.faces))]
    for e in bm.edges:
        ls = e.link_faces
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                adj[ls[i].index].append(ls[j].index)
                adj[ls[j]].append(ls[i].index) if False else adj[ls[j].index].append(ls[i].index)
    bm.free()
    return adj


def components(adj, n):
    seen = [-1] * n
    cid = 0
    for i in range(n):
        if seen[i] >= 0:
            continue
        stack = [i]
        seen[i] = cid
        while stack:
            cur = stack.pop()
            for nb in adj[cur]:
                if seen[nb] < 0:
                    seen[nb] = cid
                    stack.append(nb)
        cid += 1
    return np.array(seen), cid


def uv_islands(me):
    """UV islands: loops connected through shared vertex+uv continuity."""
    nloops = len(me.uv_layers.active.data)
    uv = me.uv_layers.active.data
    parent = list(range(nloops))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # loops of the same face are connected
    for p in me.polygons:
        ls = list(p.loop_indices)
        for k in range(1, len(ls)):
            union(ls[0], ls[k])
    # loops sharing a vertex with (near) equal uv
    by_vert = {}
    for p in me.polygons:
        for li in p.loop_indices:
            by_vert.setdefault(me.loops[li].vertex_index, []).append(li)
    for lis in by_vert.values():
        for i in range(len(lis)):
            for j in range(i + 1, len(lis)):
                a, b = lis[i], lis[j]
                du = uv[a].uv[0] - uv[b].uv[0]
                dv = uv[a].uv[1] - uv[b].uv[1]
                if abs(du) < 1e-5 and abs(dv) < 1e-5:
                    union(a, b)
    roots = {}
    island_of_loop = np.empty(nloops, dtype=np.int64)
    for li in range(nloops):
        r = find(li)
        if r not in roots:
            roots[r] = len(roots)
        island_of_loop[li] = roots[r]
    island_of_face = np.empty(len(me.polygons), dtype=np.int64)
    for p in me.polygons:
        island_of_face[p.index] = island_of_loop[p.loop_indices[0]]
    return island_of_face, len(roots)


report = {}
for tag, cfg in TOOLS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mimg, mbuf, mw, mh = load_raw(cfg['metal'])
    cimg, cbuf, cw, ch = load_raw(cfg['base'])
    bpy.ops.import_scene.fbx(filepath=cfg['src'])
    ob = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    me = ob.data
    world = ob.matrix_world
    centers = np.array([list(world @ p.center) for p in me.polygons])
    uvc = face_uv_centroids(me)
    metal_px = sample(mbuf, mw, mh, uvc)[:, cfg['channel']]
    base_px = sample(cbuf, cw, ch, uvc)
    adj = face_adjacency(me)
    comp, ncomp = components(adj, len(me.polygons))
    entry = {'faces': len(me.polygons), 'z_range': [round(float(centers[:, 2].min()), 4),
                                                    round(float(centers[:, 2].max()), 4)],
             'components': [], 'islands': [], 'bands': []}
    for c in range(ncomp):
        m = comp == c
        if m.sum() < 8:
            continue
        entry['components'].append({
            'id': c, 'faces': int(m.sum()),
            'z': [round(float(centers[m, 2].min()), 4), round(float(centers[m, 2].max()), 4)],
            'xspan': round(float(centers[m, 0].max() - centers[m, 0].min()), 4),
            'metallic_mean': round(float(metal_px[m].mean()), 4),
            'metallic_p90': round(float(np.percentile(metal_px[m], 90)), 4),
            'chroma_mean': round(float((base_px[m, 0] - base_px[m, 2]).mean()), 4),
        })
    isl, nisl = uv_islands(me)
    order = np.argsort([-int((isl == i).sum()) for i in range(nisl)])
    for i in order[:24]:
        m = isl == i
        entry['islands'].append({
            'id': int(i), 'faces': int(m.sum()),
            'z': [round(float(centers[m, 2].min()), 4), round(float(centers[m, 2].max()), 4)],
            'metallic_mean': round(float(metal_px[m].mean()), 4),
            'metallic_p90': round(float(np.percentile(metal_px[m], 90)), 4),
            'chroma_mean': round(float((base_px[m, 0] - base_px[m, 2]).mean()), 4),
        })
    z0, z1, step = cfg['bands']
    z = z0
    while z < z1 - 1e-9:
        m = (centers[:, 2] >= z) & (centers[:, 2] < z + step)
        if m.sum():
            entry['bands'].append({
                'z': round(z, 3), 'faces': int(m.sum()),
                'xspan': round(float(centers[m, 0].max() - centers[m, 0].min()), 4),
                'metallic_mean': round(float(metal_px[m].mean()), 4),
                'chroma_mean': round(float((base_px[m, 0] - base_px[m, 2]).mean()), 4),
            })
        z += step
    report[tag] = entry
    bpy.data.images.remove(mimg)
    bpy.data.images.remove(cimg)

with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=1)
print('RESPLIT_ANALYSIS_DONE', flush=True)
