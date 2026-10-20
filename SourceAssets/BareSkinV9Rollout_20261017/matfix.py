"""Commandlet: give the weapon triangles their original material slots back (Work/matprobe_report.json fix_source:
source-model triangle -> slot index, from the Before/ original's render material). Only material ids change;
then every corrective on the asset is written again (the mesh write drops them): mesh payload JC_ shapes and the
installed JC_Pose shapes. The asset must still be what this rollout last wrote.
Receipts: InstalledMat/<key>.json; Installed_pose/<key>.json is moved to <key>.r1.json and replaced by the new
state so later JC_Pose rounds accept it."""
import json, hashlib, shutil, gc
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
E = u.EditorAssetLibrary; G = u.GeometryScript_AssetUtils; Ed = u.GeometryScript_MeshEdits
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
DONE = R / 'InstalledMat'; DONE.mkdir(exist_ok=True)
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def disk(path): return P / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def payload(key, sub):
    for b in ('batch1', 'batch2', 'batch3', 'batch4'):
        f = R / 'Work' / (b + sub) / (key + '.json')
        if f.exists(): return json.loads(f.read_text())
    return None


import os
report = json.loads((R / os.environ.get('V9R_MAT_REPORT', 'Work/matprobe_report_orig.json')).read_text())
MIN_FIX = int(os.environ.get('V9R_MIN_FIX', '20'))      # a handful of boundary triangles is matching noise, not a scramble
for key, rep in sorted(report.items()):
    # only the slot permutation of a write-back scramble is repaired (whole slots, closed cycles)
    rep['fix_source'] = rep.get('fix_source_perm') or {}
    if len(rep['fix_source']) < MIN_FIX: continue
    rec = DONE / (key + '.json')
    if rec.exists(): continue
    path = rep['path']; name = path.split('/')[-1]
    try:
        if path in dirty: raise RuntimeError('package dirty')
        f = disk(path); now = sha(f)
        ok = [json.loads((R / d / (key + '.json')).read_text()).get('sha256') for d in ('Installed', 'Installed_pose', 'Installed_pose2') if (R / d / (key + '.json')).exists()]
        if now not in ok: raise RuntimeError('asset changed since the last rollout write')
        mesh = u.load_asset(path + '.' + name); slots = [s.copy() for s in mesh.materials]; lods = S.get_lod_count(mesh)
        dm, st = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
        if st != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('read')
        if u.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm) != rep['source_triangles']: raise RuntimeError('triangle count changed')
        for t, mid in rep['fix_source'].items():
            u.GeometryScript_Materials.set_triangle_material_id(dm, int(t), int(mid), True)
        opts = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True, replace_materials=True,
            new_materials=[s.material_interface for s in slots], new_material_slot_names=[s.get_editor_property('imported_material_slot_name') for s in slots],
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _, st = G.copy_mesh_to_skeletal_mesh(dm, mesh, opts, u.GeometryScriptMeshWriteLOD())
        if st != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('write')
        if lods > 1 and not S.regenerate_lod(mesh, lods, True, False): raise RuntimeError('LOD rebuild')
        # every corrective again: mesh payload (JC_, JC_Grip_) + the installed JC_Pose round
        morphs = {}
        # the JC_Pose round that is on the asset now: R2 if it was installed already, else R1
        mp = payload(key, ''); pp = payload(key, '_pose2') if (R / 'Installed_pose2' / (key + '.json')).exists() else payload(key, '_pose')
        for p_ in (mp, pp):
            if p_: morphs.update(p_.get('morphs') or {})
        names = list(morphs)
        for name_ in names:
            md, _ = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
            for vid, x, y, z, nx, ny, nz in morphs[name_]:
                Ed.set_vertex_position(md, int(vid), u.Vector(x, y, z), True)
                u.GeometryScript_Normals.update_vertex_normal(md, int(vid), True, u.Vector(nx, ny, nz), False, u.Vector(1, 0, 0), u.Vector(0, 1, 0), False, True)
            mo = u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True, emit_transaction=False,
                                                              defer_mesh_post_edit_change=name_ != names[-1], copy_normals=True)
            _, oc = G.copy_morph_target_to_skeletal_mesh(md, mesh, name_, mo, u.GeometryScriptMeshWriteLOD())
            if oc != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('morph ' + name_)
        mesh.set_editor_property('materials', slots)
        if not E.save_loaded_asset(mesh, False): raise RuntimeError('save')
        # readback: material ids of the fixed triangles
        rb, _ = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
        _, ids, _ = u.GeometryScript_Materials.get_all_triangle_material_i_ds(rb); ids = list(u.GeometryScript_List.convert_index_list_to_array(ids))
        wrong = sum(1 for t, mid in rep['fix_source'].items() if ids[int(t)] != int(mid))
        on_asset = [m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])]
        row = dict(path=path, fixed_triangles=len(rep['fix_source']), still_wrong=wrong, morphs_rewritten=len(names), morphs_on_asset=len(on_asset),
                   by_pair=rep['by_pair'], sha_before=now, sha256=sha(f), runtime_tested=False)
        rec.write_text(json.dumps(row, indent=1))
        for dname in ('Installed_pose', 'Installed_pose2'):
            pr = R / dname / (key + '.json')
            if pr.exists():
                shutil.copy2(pr, R / dname / (key + '.before_matfix.json'))
                d = json.loads(pr.read_text()); d['sha256'] = row['sha256']; d['material_fix'] = True; pr.write_text(json.dumps(d, indent=1))
        print('V9R_MATFIX', json.dumps(dict(path=path, fixed=len(rep['fix_source']), still_wrong=wrong)), flush=True)
    except Exception as e:
        (DONE / (key + '.failed.json')).write_text(json.dumps(dict(path=path, error=str(e))))
        print('V9R_MATFIX_FAIL', path, str(e), flush=True)
    gc.collect(); u.SystemLibrary.collect_garbage()
print('V9R_MATFIX_COMPLETE', flush=True)
