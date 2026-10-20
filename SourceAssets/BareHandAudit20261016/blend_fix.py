"""Blender (background): apply the V8 surface repair to editable sources that carry bare arms.

Usage: blender -b --factory-startup --python blend_fix.py -- <blend> [<blend> ...]

Only mesh objects with hand_l/hand_r groups are considered, and only their
bare-skin polygons (material names like Manny/Bare/Skin/Arms/Hand, never
glove/sleeve/cloth). The mesh is edited in place with bmesh: listed faces are
removed and replacement faces are created on the existing vertices with every
loop layer (UVs, colours) copied from the source corners; custom normals are
carried through a temporary corner attribute. Vertices, groups, edges and all
other polygons keep their data. Rig, actions and modifiers are untouched.
Backups go to Before/<relative path>; a receipt is written per file.
"""
import bpy, bmesh, json, re, sys, shutil, traceback
from pathlib import Path
R = Path(__file__).resolve().parent; P = R.parents[1]; sys.path.insert(0, str(R))
from generic_fix import plan_mesh
from fbx_fix import is_skin
bpy.context.preferences.filepaths.save_version = 0
files = [Path(x) for x in sys.argv[sys.argv.index('--') + 1:] if x != '--check']
OUT = R / ('BlendChecks' if '--check' in sys.argv else 'Blends'); OUT.mkdir(exist_ok=True)


CHECK = '--check' in sys.argv


def repair(obj, file_time):
    mesh = obj.data
    if mesh.library: return None                       # linked library data is never saved into this file
    if mesh.shape_keys: return dict(object=obj.name, skipped='shape keys present')
    skin_mats = {i for i, m in enumerate(mesh.materials) if m and is_skin(m.name.split('.')[0] if m.name.startswith('MI_Manny_') else m.name, file_time)}
    if not mesh.materials: skin_mats = {0}
    polys = [p for p in mesh.polygons if p.material_index in skin_mats]
    if not polys: return None
    if any(len(p.vertices) != 3 for p in polys): return dict(object=obj.name, skipped='skin polygons are not triangles')
    orig = [p.index for p in polys]
    cn = [tuple(n.vector) for n in mesh.corner_normals]
    first_uv = mesh.uv_layers.active or (mesh.uv_layers[0] if mesh.uv_layers else None)
    d = dict(positions=[list(v.co * 100) for v in mesh.vertices], triangles=[list(p.vertices) for p in polys],
             normals=[[cn[li] for li in p.loop_indices] for p in polys],
             uv=[[tuple(first_uv.data[li].uv) for li in p.loop_indices] for p in polys] if first_uv else [[(0, 0)] * 3 for _ in polys],
             triangle_materials=[p.material_index for p in polys], weights=[{} for _ in mesh.vertices])
    ops = plan_mesh(d)
    if not (ops['remove'] or ops['add'] or ops['normals']): return None
    if CHECK: return dict(object=obj.name, pending=dict(ops['notes']))
    rep = ops['rep']
    # Carry every loop normal through bmesh in a temporary corner attribute.
    tmp = mesh.attributes.new('_v8_normal', 'FLOAT_VECTOR', 'CORNER')
    tmp.data.foreach_set('vector', [c for n in cn for c in n])
    bm = bmesh.new(); bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    nl = bm.loops.layers.float_vector['_v8_normal']
    uvl = list(bm.loops.layers.uv.values())
    col = list(bm.loops.layers.color.values()) + list(bm.loops.layers.float_color.values())
    def source(ti, k):
        f = bm.faces[orig[ti]]; return f, list(f.loops)[k]
    # Normal overrides on kept faces.
    for (ti, k), nn in ops['normals'].items():
        _, loop = source(ti, k); loop[nl] = nn
    snapshots = []
    for a in ops['add']:
        corners = []
        for k, (ti, kk, ov) in enumerate(a['corners']):
            f, loop = source(ti, kk)
            vi = rep[ov] if ov is not None else d['triangles'][ti][kk]
            nn = a.get('normals', {}).get(k) or a.get('normals', {}).get(str(k)) or list(loop[nl])
            corners.append(dict(v=vi, uv=[tuple(loop[l].uv) for l in uvl], col=[tuple(loop[l]) for l in col], n=nn,
                                mat=f.material_index, smooth=f.smooth))
        snapshots.append(corners)
    bmesh.ops.delete(bm, geom=[bm.faces[orig[i]] for i in ops['remove']], context='FACES_ONLY')
    for corners in snapshots:
        f = bm.faces.new([bm.verts[c['v']] for c in corners])
        f.material_index = corners[0]['mat']; f.smooth = corners[0]['smooth']
        for loop, c in zip(f.loops, corners):
            for l, uv in zip(uvl, c['uv']): loop[l].uv = uv
            for l, cc in zip(col, c['col']): loop[l] = cc
            loop[nl] = c['n']
    bm.to_mesh(mesh); bm.free(); mesh.update()
    vals = [0.0] * (len(mesh.loops) * 3)
    mesh.attributes['_v8_normal'].data.foreach_get('vector', vals)
    mesh.normals_split_custom_set([tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)])
    mesh.attributes.remove(mesh.attributes['_v8_normal'])
    return dict(object=obj.name, removed=len(ops['remove']), added=len(ops['add']), normal_corners=len(ops['normals']), notes=dict(ops['notes']))


for file in files:
    receipt = OUT / (file.parent.name + '__' + file.stem + '.json')
    if receipt.exists(): continue
    try:
        bpy.ops.wm.open_mainfile(filepath=str(file))
    except Exception as exc:
        receipt.write_text(json.dumps(dict(path=str(file), error='open failed: %s' % exc), indent=1)); continue
    changes = []
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or obj.library or not any(g.name in ('hand_r', 'hand_l') for g in obj.vertex_groups): continue
        try:
            row = repair(obj, file.stat().st_mtime)
        except Exception:
            row = dict(object=obj.name, error=traceback.format_exc(limit=2))
        if row: changes.append(row)
    if any('removed' in c for c in changes):
        backup = R / 'Before' / file.relative_to(P); backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists(): shutil.copy2(file, backup)
        bpy.ops.wm.save_as_mainfile(filepath=str(file))
    receipt.write_text(json.dumps(dict(path=str(file), changes=changes), indent=1))
    print('BARE_V8_BLEND', file.name, changes, flush=True)
print('BARE_V8_BLEND_COMPLETE', len(files), flush=True)
