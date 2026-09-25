"""v2 拆分：按语义（连通域金属度/色度）区分金属头与木棍、绳缠，替换 v1 的纯 Z 切。

用户反馈 v1 的镐把前端绳缠和木棍也划进了 Metal。v2 规则（数据见 resplit-analysis.json）：
  镐＝连通域规则：metallic_mean>=0.15 且 chroma_mean<=0.16 且 z_min>=z_gate 的连通域判金属。
      绳缠/木棍域 metallic≈0.001 不进；穿出头顶的木棍帽域 chroma 0.18-0.30 被色度挡掉。
  斧＝逐面规则：z>=z_gate 且 (chroma<0.20 或 metallic>0.2)。斧柄色度 0.27-0.30、斧头 0.006-0.15，
      可分；顺带排除穿入头部的柄顶（色度高）。
导出/回读校验/复核渲染沿用 v1 流程，输出覆盖 SourceAssets/ToolEnhance20260925/Export/。
"""
import bpy
import bmesh
import json
import os
import sys
import numpy as np
from mathutils import Vector

ROOT = 'D:/FPS3D/FPSGAME/SourceAssets'
HERE = ROOT + '/ToolEnhance20260925'
OUT = HERE + '/Export'
REVIEW = 'D:/FPS3D/FPSGAME/Saved/Production'
os.makedirs(OUT, exist_ok=True)
os.makedirs(REVIEW, exist_ok=True)

AXE_INPUT = ROOT + '/BattleAxeReplace20260919/Input/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx'
AXE_MAPS = {
    'metallic': AXE_INPUT + '/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_metallic.png',
    'basecolor': AXE_INPUT + '/Meshy_AI_Weathered_Battle_Axe_0918025738_texture.png',
}
PICK_MAPS = {
    'metallic': ROOT + '/RusticPickaxe20260919/Textures/MetallicRoughness.jpg',
    'basecolor': ROOT + '/RusticPickaxe20260919/Textures/BaseColor.jpg',
}

TOOLS = {
    'axe': {
        'maps': AXE_MAPS, 'metal_channel': 0, 'rule': 'face',
        'z_gate': 0.195, 'chroma_max': 0.20, 'metal_seed': 0.2,
        'export_kwargs': dict(use_selection=True, object_types={'MESH'}, global_scale=1.0,
                              apply_unit_scale=True, axis_forward='-Y', axis_up='Z',
                              mesh_smooth_type='FACE', bake_anim=False,
                              use_mesh_modifiers=True, add_leaf_bones=False),
        'targets': [
            ('BattleAxe_16000', ROOT + '/BattleAxeReplace20260919/Fitted/BattleAxe_16000.fbx', 16000),
            ('BattleAxe_LOD1', ROOT + '/BattleAxeReplace20260919/Fitted/BattleAxe_LOD1.fbx', 2500),
            ('BattleAxe_LOD2', ROOT + '/BattleAxeReplace20260919/Fitted/BattleAxe_LOD2.fbx', 600),
        ],
    },
    'pickaxe': {
        'maps': PICK_MAPS, 'metal_channel': 2, 'rule': 'component',
        'z_gate': 0.33, 'comp_metallic_min': 0.15, 'comp_chroma_max': 0.16,
        'export_kwargs': dict(use_selection=True, object_types={'MESH'}, axis_forward='-Y',
                              axis_up='Z', mesh_smooth_type='FACE', use_tspace=True,
                              bake_anim=False, add_leaf_bones=False, path_mode='STRIP'),
        'targets': [
            ('RusticPickaxe_World', ROOT + '/RusticPickaxe20260919/Export/RusticPickaxe_World.fbx', 32000),
            ('RusticPickaxe_LOD1', ROOT + '/RusticPickaxe20260919/Export/RusticPickaxe_LOD1.fbx', 8000),
            ('RusticPickaxe_LOD2', ROOT + '/RusticPickaxe20260919/Export/RusticPickaxe_LOD2.fbx', 2000),
        ],
    },
}

REPORT_PATH = HERE + '/material-regions-v2.json'
report = {'rule_version': 2, 'tools': {}}


def fail(msg):
    print('SPLIT_FAIL: ' + msg)
    sys.exit(1)


def dump_report():
    with open(REPORT_PATH, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)


def load_raw(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = int(img.size[0]), int(img.size[1])
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return img, np.flipud(buf.reshape(h, w, 4)), w, h


def sample_rgb(buf, w, h, uv):
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
                adj[ls[j].index].append(ls[i].index)
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


def build_mask(tag, cfg, centers, metal_px, chroma, me):
    z = centers[:, 2]
    if cfg['rule'] == 'face':
        return (z >= cfg['z_gate']) & ((chroma < cfg['chroma_max']) | (metal_px > cfg['metal_seed'])), {}
    adj = face_adjacency(me)
    comp, ncomp = components(adj, len(me.polygons))
    metal_comps = []
    detail = []
    for c in range(ncomp):
        m = comp == c
        if m.sum() < 4:
            continue
        mmean = float(metal_px[m].mean())
        cmean = float(chroma[m].mean())
        zmin = float(centers[m, 2].min())
        is_metal = mmean >= cfg['comp_metallic_min'] and cmean <= cfg['comp_chroma_max'] and zmin >= cfg['z_gate']
        if is_metal:
            metal_comps.append(c)
        if zmin >= cfg['z_gate'] - 0.05:
            detail.append({'comp': c, 'faces': int(m.sum()), 'metallic': round(mmean, 4),
                           'chroma': round(cmean, 4), 'zmin': round(zmin, 4), 'metal': bool(is_metal)})
    mask = np.isin(comp, metal_comps) if metal_comps else np.zeros(len(me.polygons), dtype=bool)
    return mask, {'metal_components': metal_comps, 'high_components': detail}


def render_review(ob, tag):
    scene = bpy.context.scene
    for mat in ob.data.materials:
        if mat is None:
            continue
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf is None:
            continue
        metal = 'metal' in mat.name.lower()
        mat.diffuse_color = (0.55, 0.62, 0.70, 1.) if metal else (0.36, 0.22, 0.12, 1.)
        bsdf.inputs['Base Color'].default_value = (0.55, 0.62, 0.70, 1.) if metal else (0.36, 0.22, 0.12, 1.)
        bsdf.inputs['Metallic'].default_value = 1.0 if metal else 0.0
        bsdf.inputs['Roughness'].default_value = 0.35 if metal else 0.85
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 760
    scene.render.resolution_y = 1000
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('ReviewWorld') if not scene.world else scene.world
    me = ob.data
    world = ob.matrix_world
    pts = np.array([list(world @ v.co) for v in me.vertices])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    center = (lo + hi) / 2.
    radius = float(np.linalg.norm(hi - lo)) / 2.
    for view, direction in (('front', Vector((0., -1., 0.))), ('side', Vector((1., 0., 0.)))):
        cam_data = bpy.data.cameras.new('ReviewCam_' + view)
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = radius * 2.35
        cam = bpy.data.objects.new('ReviewCam_' + view, cam_data)
        scene.collection.objects.link(cam)
        cam.location = center + direction * (radius * 3.)
        cam.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        scene.camera = cam
        scene.render.filepath = os.path.join(REVIEW, 'tool-enhance-v2-split-%s-%s.png' % (tag, view))
        bpy.ops.render.render(write_still=True)
        scene.collection.objects.unlink(cam)
        bpy.data.objects.remove(cam, do_unlink=False)
        bpy.data.cameras.remove(cam_data)


only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

for tag, cfg in TOOLS.items():
    if only and tag not in only:
        continue
    mimg, mbuf, mw, mh = load_raw(cfg['maps']['metallic'])
    cimg, cbuf, cw, ch = load_raw(cfg['maps']['basecolor'])
    tool_report = {'rule': cfg['rule'], 'z_gate': cfg['z_gate'], 'targets': {}}
    for name, src, expect_tris in cfg['targets']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=src)
        meshes = [o for o in bpy.data.objects if o.type == 'MESH']
        if len(meshes) != 1:
            fail('%s: expected 1 mesh, got %d' % (name, len(meshes)))
        ob = meshes[0]
        me = ob.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        if tris != expect_tris:
            fail('%s: tris %d != baseline %d' % (name, tris, expect_tris))
        world = ob.matrix_world
        centers = np.array([list(world @ p.center) for p in me.polygons])
        uvc = face_uv_centroids(me)
        metal_px = sample_rgb(mbuf, mw, mh, uvc)[:, cfg['metal_channel']]
        base_px = sample_rgb(cbuf, cw, ch, uvc)
        chroma = base_px[:, 0] - base_px[:, 2]
        mask, detail = build_mask(tag, cfg, centers, metal_px, chroma, me)
        if mask.sum() == 0:
            fail('%s: empty metal mask' % name)

        for existing in list(me.materials):
            me.materials.pop(index=0)
        # 源 FBX 的材质 datablock 弹掉槽引用后仍是孤儿，若同名会让新槽变 .001
        for leftover in list(bpy.data.materials):
            if leftover.users == 0:
                bpy.data.materials.remove(leftover)
        mat_metal = bpy.data.materials.new('Metal')
        mat_metal.use_nodes = True
        mat_wood = bpy.data.materials.new('Wood')
        mat_wood.use_nodes = True
        me.materials.append(mat_metal)
        me.materials.append(mat_wood)
        for p in me.polygons:
            p.material_index = 0 if mask[p.index] else 1
        me.update()

        dest = os.path.join(OUT, name + '.fbx')
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=dest, **cfg['export_kwargs'])

        base_pts = np.array([list(world @ v.co) for v in me.vertices])
        base_lo, base_hi = base_pts.min(axis=0), base_pts.max(axis=0)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=dest)
        back = [o for o in bpy.data.objects if o.type == 'MESH']
        if len(back) != 1:
            fail('%s: reimport got %d meshes' % (name, len(back)))
        bme = back[0].data
        bworld = back[0].matrix_world
        btris = sum(len(p.vertices) - 2 for p in bme.polygons)
        bpts = np.array([list(bworld @ v.co) for v in bme.vertices])
        blo, bhi = bpts.min(axis=0), bpts.max(axis=0)
        slots = [m.name if m else None for m in bme.materials]
        per_slot = {}
        for p in bme.polygons:
            key = slots[p.material_index] if p.material_index < len(slots) else '?'
            per_slot[key] = per_slot.get(key, 0) + 1
        drift = float(np.max(np.abs(blo - base_lo)) + np.max(np.abs(bhi - base_hi)))
        verify = {'tris_before': tris, 'tris_after': btris, 'slots_after': slots,
                  'faces_per_slot': per_slot, 'bounds_drift': round(drift, 6)}
        if btris != tris:
            fail('%s: tris changed %d -> %d' % (name, tris, btris))
        if slots != ['Metal', 'Wood']:
            fail('%s: slots %s' % (name, slots))
        if not bme.uv_layers:
            fail('%s: no uv layers' % name)
        if drift > 2e-3:
            fail('%s: bounds drift %.5f' % (name, drift))

        if name.endswith(('16000', 'World')):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=dest)
            render_review([o for o in bpy.data.objects if o.type == 'MESH'][0], tag)
            verify['review'] = ['%s/tool-enhance-v2-split-%s-%s.png' % (REVIEW, tag, v)
                                for v in ('front', 'side')]

        tool_report['targets'][name] = {'output': dest, 'metal_faces': int(mask.sum()),
                                        'metal_frac': round(float(mask.mean()), 4),
                                        'detail': detail, 'verify': verify}
        print('SPLIT_V2_OK %s metal=%d/%d (%.1f%%)' % (name, int(mask.sum()), len(mask),
                                                       100. * float(mask.mean())), flush=True)
        dump_report()
    for img in (mimg, cimg):
        try:
            bpy.data.images.remove(img)
        except ReferenceError:
            pass
    report['tools'][tag] = tool_report
    dump_report()

print('SPLIT_V2_ALL_PASS')
