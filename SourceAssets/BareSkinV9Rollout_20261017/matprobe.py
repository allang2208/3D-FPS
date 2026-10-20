"""Commandlet (read-only for project assets): per installed mesh, the render material slot (name) of every non-skin
triangle now and in the Before/ original (a temporary copy under /Game/__V9Probe, deleted afterwards).
Suspected: the V9 install wrote material ids that were polygon-group indices of the original mesh description
as slot indices, so weapon parts on meshes whose group order differs from the slot order got the wrong material.
-> Work/MatProbe/<key>.json"""
import json, shutil, gc, os
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
OUT = R / os.environ.get('V9R_PROBE_OUT', 'Work/MatProbe'); OUT.mkdir(exist_ok=True)
BEFORE = Path(os.environ.get('V9R_BEFORE_ROOT', str(R / 'Before')))       # older backups can be compared too
G = u.GeometryScript_AssetUtils; Q = u.GeometryScript_MeshQueries
TMP = P / 'Content/__V9Probe'


def tris(mesh, lod_type):
    opts = u.GeometryScriptCopyMeshFromAssetOptions(); rl = u.GeometryScriptMeshReadLOD(); rl.lod_type = lod_type
    dm, st = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), opts, rl)
    if st != u.GeometryScriptOutcomePins.SUCCESS: return None
    _, ids, _ = u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm); ids = list(u.GeometryScript_List.convert_index_list_to_array(ids))
    _, pos, _ = Q.get_all_vertex_positions(dm, False); pos = list(u.GeometryScript_List.convert_vector_list_to_array(pos))
    _, tl, _ = Q.get_all_triangle_indices(dm, False); tl = list(u.GeometryScript_List.convert_triangle_list_to_array(tl))
    out = []
    for mid, t in zip(ids, tl):
        a, b, c = pos[t.x], pos[t.y], pos[t.z]
        out.append([mid, round((a.x + b.x + c.x) / 3, 3), round((a.y + b.y + c.y) / 3, 3), round((a.z + b.z + c.z) / 3, 3)])
    return out


import os
ONLY = os.environ.get('V9R_ONLY', '')
import hashlib
PATHS = os.environ.get('V9R_PATHS_FILE')                                 # other meshes (e.g. V8-only ones) by list
recs = ([dict(path=p) for p in json.loads(Path(PATHS).read_text())] if PATHS else
        [json.loads(f.read_text()) for f in (R / 'Installed').glob('*.json') if f.stem.count('.') == 0])
budget = int(os.environ.get('V9R_MAX_MESHES', '30'))                   # memory: reruns resume from the outputs
for rec in recs:
    if ONLY and ONLY not in rec['path']: continue
    path = rec['path']; key = Path(rec.get('path')).name; name = path.split('/')[-1]
    k12 = hashlib.sha256(path.encode()).hexdigest()[:12] if PATHS else None
    for f in ([] if PATHS else (R / 'Installed').glob('*.json')):
        if f.stem.count('.') == 0 and json.loads(f.read_text())['path'] == path: k12 = f.stem; break
    of = OUT / (k12 + '.json')
    if of.exists(): continue
    if budget <= 0: break
    budget -= 1
    src = BEFORE / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    roots = [x for x in os.environ.get('V9R_BEFORE_ROOTS', '').split(',') if x]     # oldest backup that has it
    for rt in roots:
        cand = Path(rt) / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        if cand.exists(): src = cand; break
    if not src.exists(): of.write_text(json.dumps(dict(path=path, error='no Before copy'))); continue
    d = TMP / k12; d.mkdir(parents=True, exist_ok=True); shutil.copy2(src, d / (name + '.uasset'))
    row = dict(path=path, reference=str(src))
    try:
        cur = u.load_asset(path + '.' + name); old = u.load_asset('/Game/__V9Probe/%s/%s.%s' % (k12, name, name))
        if old is None: raise RuntimeError('temp copy did not load')
        row['slots_now'] = [str(s.get_editor_property('material_slot_name')) for s in cur.materials]
        row['slots_before'] = [str(s.get_editor_property('material_slot_name')) for s in old.materials]
        for tag, lt in (('render', u.GeometryScriptLODType.RENDER_DATA), ('source', u.GeometryScriptLODType.SOURCE_MODEL)):
            row[tag + '_now'] = tris(cur, lt); row[tag + '_before'] = tris(old, lt)
    except Exception as e:
        row['error'] = str(e)
    of.write_text(json.dumps(row, separators=(',', ':'))); print('V9R_MATPROBE', path, row.get('error', 'ok'), flush=True)
    cur = old = None; gc.collect(); u.SystemLibrary.collect_garbage()
# R3c: the copies stay until run_r3c_post.ps1 moves them out of Content (after the 10-19 loss of the Before/
# backups they are the only remaining copies of those versions); nothing is deleted here any more
print('V9R_MATPROBE_COMPLETE', flush=True)
