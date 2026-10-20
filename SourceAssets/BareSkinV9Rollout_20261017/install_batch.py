"""Commandlet (UE closed): install one rollout batch.

Meshes (Work/<batch>/<key>.json): V9 rest positions, normals, UV0, weight denoise, LOD rebuild, JC_ morphs,
skin slots -> MI_BareSkinV9. Each asset must still match its snapshot hash and be clean; the .uasset is
copied to Before/ first; a failure leaves that asset unsaved and continues.
Animations (Work/<batch>/twist_specs.json): lowerarm_twist_01/02 tracks rewritten so they carry 100% / 50%
of the hand's roll about the forearm; every other track, notify and curve is untouched.
Receipts: Installed/<key>.json, InstalledAnims/<hash>.json.
"""
import json, hashlib, shutil, math, os, gc
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
BATCH = os.environ.get('V9R_BATCH', 'batch1'); SUB = os.environ.get('V9R_SUBDIR', ''); W = R / 'Work' / (BATCH + SUB)
E = u.EditorAssetLibrary; A = u.AssetToolsHelpers.get_asset_tools(); L = u.MaterialEditingLibrary
G = u.GeometryScript_AssetUtils; Q = u.GeometryScript_MeshQueries; Ed = u.GeometryScript_MeshEdits; Bw = u.GeometryScript_BoneWeights
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
DONE = R / ('Installed' + SUB); DONE.mkdir(exist_ok=True); DONE_A = R / 'InstalledAnims'; DONE_A.mkdir(exist_ok=True)
MI_PATH = '/Game/Characters/ModularOutfit20260924/BareSkinV9/MI_BareSkinV9'
TAG = 'BareSkinV9'


def disk(path): return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def obj(path): return path if '.' in path.split('/')[-1] else path + '.' + path.split('/')[-1]


def backup(path):
    f = disk(path); b = R / 'Before' / f.relative_to(P); b.parent.mkdir(parents=True, exist_ok=True)
    if not b.exists(): shutil.copy2(f, b)


dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

# ---------------------------------------------------------------- shared material instance
mi = u.load_asset(MI_PATH)
if not mi:
    mi = A.create_asset('MI_BareSkinV9', MI_PATH.rsplit('/', 1)[0], u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi, u.load_asset('/Game/Characters/ModularOutfit20260924/BareSkinV9M4/M_M4SkinV9'))
    L.update_material_instance(mi)
    if not E.save_loaded_asset(mi, False): raise RuntimeError('Cannot save ' + MI_PATH)


# ---------------------------------------------------------------- meshes
def install_mesh(p):
    path = p['path']; f = disk(path); now = sha(f); live_ref = p.get('old_positions')     # absent on JC_Pose payloads
    if p.get('morphs_only'):
        # accepted V9 asset / installed rollout mesh: only (re)write correctives (no surface, slot or LOD change)
        prev = DONE / (p['key'] + '.prev.json'); mesh_rec = R / 'Installed' / (p['key'] + '.json')
        # R3c: memory grows with every morph written in one process (68 GB on LMG201 with ~130 shapes), so the
        # shapes go in size-scaled chunks across runs; the partial file carries the progress and the asset hash
        part_f = DONE / (p['key'] + '.partial.json'); part = json.loads(part_f.read_text()) if part_f.exists() else None
        if part:
            if part['sha256'] != now: return dict(path=path, skipped='asset changed since the last chunk')
        elif p.get('after_mesh_receipt'):
            # the asset must still be exactly what this rollout last wrote: the mesh payload, or an earlier JC_Pose round
            # (a chunked install another round left half-way counts too: this payload's stale list empties its shapes)
            recs = [R / d / (p['key'] + suf) for d in os.environ.get('V9R_ACCEPT_DIRS', 'Installed').split(',') for suf in ('.json', '.partial.json')]
            if not any(r.exists() and json.loads(r.read_text()).get('sha256') == now for r in recs):
                return dict(path=path, skipped='mesh payload not installed yet or asset changed since')
        elif now != p['sha'] and not (prev.exists() and json.loads(prev.read_text()).get('sha256') == now):
            return dict(path=path, skipped='asset changed since snapshot')
        if path in dirty: return dict(path=path, skipped='package dirty')
        backup(path); mesh = u.load_asset(obj(path)); names = list(p['morphs'])
        prefix = p.get('stale_prefix'); keep = set(p.get('keep', [])) | set(names)
        # shapes an earlier round already emptied stay empty (re-emptying them every round only costs memory)
        done_empty = set()
        for d in os.environ.get('V9R_ACCEPT_DIRS', 'Installed').split(','):
            r = R / d / (p['key'] + '.json')
            if r.exists(): done_empty |= set(json.loads(r.read_text()).get('emptied_stale_morphs', []))
        if part: stale = part['stale']; written = set(part['written'])
        else:
            stale = [m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])
                     if prefix and m.get_name().startswith(prefix) and m.get_name() not in keep and m.get_name() not in done_empty]
            written = set()
        new_names = names; names = stale + names
        todo = [x for x in names if x not in written]
        probe, _ = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
        cost = max(1.0, probe.get_triangle_count() / 100000.0); probe = None
        chunk = todo[:max(1, int(UNITS[0] / cost))]; UNITS[0] -= len(chunk) * cost
        for i, name in enumerate(chunk):
            md, st = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
            rows = p['morphs'].get(name)
            if rows is None:                          # emptied: 0.05 cm on one vertex (empty morphs are refused)
                x0 = p['positions'][0]; n0 = p['vertex_normals'][0]
                rows = [[p['vertex_ids'][0], x0[0] + .05 * n0[0], x0[1] + .05 * n0[1], x0[2] + .05 * n0[2], *n0]]
            for vid, x, y, z, nx, ny, nz in rows:
                Ed.set_vertex_position(md, int(vid), u.Vector(x, y, z), True)
                u.GeometryScript_Normals.update_vertex_normal(md, int(vid), True, u.Vector(nx, ny, nz), False, u.Vector(1, 0, 0), u.Vector(0, 1, 0), False, True)
            mo = u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True, emit_transaction=False,
                                                              defer_mesh_post_edit_change=name != chunk[-1], copy_normals=True)
            _, oc = G.copy_morph_target_to_skeletal_mesh(md, mesh, name, mo, u.GeometryScriptMeshWriteLOD())
            if oc != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('morph ' + name)
            md = None
        written |= set(chunk)
        if len(written) < len(names):
            if chunk and not E.save_loaded_asset(mesh, False): raise RuntimeError('save')
            part_f.write_text(json.dumps(dict(path=path, sha256=sha(f), stale=stale, written=sorted(written), total=len(names))))
            return dict(path=path, partial=True, written=len(written), total=len(names))
        added = new_names
        all_empty = stale + sorted(done_empty - set(added))  # the receipt keeps the full list of emptied shapes
        E.set_metadata_tag(mesh, TAG + ('_Poses' if SUB else '_Grips'), '20261017 rollout: %d correctives written, %d emptied' % (len(added), len(all_empty)))
        if names and not E.save_loaded_asset(mesh, False): raise RuntimeError('save')
        if part_f.exists(): part_f.unlink()
        on_asset = [m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])]
        return dict(path=path, saved=True, morphs=len(added), morphs_on_asset=len(on_asset), added=added, emptied_stale_morphs=all_empty,
                    position_readback_max_cm=0.0, sha256=sha(f), runtime_tested=False)
    if now != p['sha']:
        # re-install over this rollout's own earlier install only (receipt hash + its payload positions)
        prev = DONE / (p['key'] + '.prev.json'); prev_payload = W.parent / (BATCH + '_prev') / (p['key'] + '.json')
        if not (prev.exists() and prev_payload.exists() and json.loads(prev.read_text()).get('sha256') == now):
            return dict(path=path, skipped='asset changed since snapshot')
        live_ref = json.loads(prev_payload.read_text())['positions']
    if path in dirty: return dict(path=path, skipped='package dirty')
    mesh = u.load_asset(obj(path)); slots = [s.copy() for s in mesh.materials]; lods = S.get_lod_count(mesh)
    dm, st = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if st != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('read')
    _, ps, _ = Q.get_all_vertex_positions(dm, False); ps = list(u.GeometryScript_List.convert_vector_list_to_array(ps))
    vids = p['vertex_ids']; worst = 0.0
    for vid, old in zip(vids[::7], live_ref[::7]):
        q = ps[vid]; worst = max(worst, abs(q.x - old[0]), abs(q.y - old[1]), abs(q.z - old[2]))
    if worst > 1e-3: return dict(path=path, skipped='live skin differs from snapshot (%.4f)' % worst)
    backup(path)
    for vid, x in zip(vids, p['positions']): ps[vid] = u.Vector(*x)
    Ed.set_all_mesh_vertex_positions(dm, u.GeometryScript_List.convert_array_to_vector_list(ps))
    for vid, n in zip(vids, p['vertex_normals']):
        u.GeometryScript_Normals.update_vertex_normal(dm, vid, True, u.Vector(*n), False, u.Vector(1, 0, 0), u.Vector(0, 1, 0), False, True)
    for tid, uv in zip(p['triangle_ids'], p['uv0']):
        u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm, 0, tid, u.GeometryScriptUVTriangle(uv0=u.Vector2D(*uv[0]), uv1=u.Vector2D(*uv[1]), uv2=u.Vector2D(*uv[2])), True)
    _, bones = Bw.get_all_bones_info(dm); bid = {str(b.name): b.index for b in bones}
    for vid, row in p['weights'].items():
        Bw.set_vertex_bone_weights(dm, int(vid), [u.GeometryScriptBoneWeight(bone_index=bid[b], weight=w) for b, w in row.items() if b in bid])
    opts = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True, replace_materials=True,
        new_materials=[s.material_interface for s in slots], new_material_slot_names=[s.get_editor_property('imported_material_slot_name') for s in slots],
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, st = G.copy_mesh_to_skeletal_mesh(dm, mesh, opts, u.GeometryScriptMeshWriteLOD())
    if st != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('write')
    if lods > 1 and not S.regenerate_lod(mesh, lods, True, False): raise RuntimeError('LOD rebuild')
    names = list(p['morphs'])
    # correctives of an earlier install that this payload no longer has: emptied (zero delta), so the
    # runtime driver, which reads the grip names from the asset, never drives a stale shape
    stale = [m.get_name() for m in (mesh.get_editor_property('morph_targets') or []) if m.get_name().startswith('JC_') and m.get_name() not in names]
    for name in stale + names:
        md, st = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
        rows = p['morphs'].get(name)
        if rows is None:                              # empty / sub-threshold morphs are refused: 0.05 cm on one vertex
            x0 = p['positions'][0]; n0 = p['vertex_normals'][0]
            rows = [[vids[0], x0[0] + .05 * n0[0], x0[1] + .05 * n0[1], x0[2] + .05 * n0[2], *n0]]
        for vid, x, y, z, nx, ny, nz in rows:
            Ed.set_vertex_position(md, int(vid), u.Vector(x, y, z), True)
            u.GeometryScript_Normals.update_vertex_normal(md, int(vid), True, u.Vector(nx, ny, nz), False, u.Vector(1, 0, 0), u.Vector(0, 1, 0), False, True)
        mo = u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True, emit_transaction=False,
                                                          defer_mesh_post_edit_change=name != (stale + names)[-1], copy_normals=True)
        _, oc = G.copy_morph_target_to_skeletal_mesh(md, mesh, name, mo, u.GeometryScriptMeshWriteLOD())
        if oc != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('morph ' + name)
    for i, s in enumerate(slots):
        if i in p['skin_slots']: s.set_editor_property('material_interface', mi)
    mesh.set_editor_property('materials', slots)
    E.set_metadata_tag(mesh, TAG, '20261017 rollout %s: M4 V9 surface, UV0 skin, JC_ correctives (pose source %s)' % (BATCH, p['pose_source']))
    if not E.save_loaded_asset(mesh, False): raise RuntimeError('save')
    rb, _ = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    _, qs, _ = Q.get_all_vertex_positions(rb, False); qs = u.GeometryScript_List.convert_vector_list_to_array(qs)
    err = max(max(abs(qs[v].x - x[0]), abs(qs[v].y - x[1]), abs(qs[v].z - x[2])) for v, x in zip(vids[::5], p['positions'][::5]))
    on_asset = [m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])]
    return dict(path=path, saved=True, morphs=len(names), morphs_on_asset=len(on_asset), emptied_stale_morphs=stale,
                lods=S.get_lod_count(mesh), position_readback_max_cm=err, sha256=sha(f), runtime_tested=False)


files = sorted(f for f in W.glob('*.json') if len(f.stem) == 12 and all(c in '0123456789abcdef' for c in f.stem))
# bounded per commandlet (memory); reruns resume from receipts. 6 since R3c: with ~100 JC_Pose shapes a mesh,
# 12 ran out of memory (32 GB machine)
budget = int(os.environ.get('V9R_MAX_MESHES', '6'))
UNITS = [float(os.environ.get('V9R_MORPH_UNITS', '60'))]  # morphs per run, x (triangles / 100k); 80 peaked at 30 GB
for n, f in enumerate(files):
    p = json.loads(f.read_text()); rec = DONE / (p['key'] + '.json')
    if rec.exists(): continue
    if budget <= 0 or UNITS[0] <= 0: print('V9R_MESH_BUDGET_REACHED', flush=True); break
    budget -= 1
    try: row = install_mesh(p)
    except Exception as e: row = dict(path=p['path'], error=str(e))
    if row.get('partial'): print('V9R_MESH_PARTIAL', json.dumps(row), flush=True); p = None; gc.collect(); u.SystemLibrary.collect_garbage(); continue
    (rec if row.get('saved') else DONE / (p['key'] + '.failed.json')).write_text(json.dumps(row, indent=1))
    print('V9R_MESH', json.dumps(row), flush=True)
    p = None; gc.collect(); u.SystemLibrary.collect_garbage()


# ---------------------------------------------------------------- animations: forearm twist
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(a): return (-a[0], -a[1], -a[2], a[3])


def qaxis(axis, deg):
    h = math.radians(deg) / 2; s = math.sin(h); return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(h))


def twist(q, axis):
    x, y, z, w = q
    if w < 0: x, y, z, w = -x, -y, -z, -w
    return math.degrees(2 * math.atan2(x * axis[0] + y * axis[1] + z * axis[2], w))


def qt(uq): return (uq.x, uq.y, uq.z, uq.w)


# Superseded by anim_fix_raw.py (data-model reader); kept only for reference: the compressed reader it used can
# return the reference pose on the first evaluations after a load.
specs = json.loads((W / 'twist_specs.json').read_text()) if os.environ.get('V9R_LEGACY_TWIST') == '1' and (W / 'twist_specs.json').exists() else {}
mesh_cache = {}
for path, spec in specs.items():
    rec = DONE_A / (hashlib.sha256(path.encode()).hexdigest()[:12] + '.json')
    if rec.exists(): continue
    try:
        if path in dirty: raise RuntimeError('package dirty')
        seq = u.load_asset(obj(path)); f = disk(path); before = sha(f)
        vm = spec['mesh']; mesh_cache.setdefault(vm, u.load_asset(obj(vm))); mesh = mesh_cache[vm]
        # compressed evaluation: raw evaluation returned bind-pose hands on a few isolated keys
        opts = u.AnimPoseEvaluationOptions(); opts.optional_skeletal_mesh = mesh; opts.evaluation_type = u.AnimDataEvalType.COMPRESSED
        # keys of the data model itself: the sampled-key count can be a multiple of it (240 vs 120 fps), and
        # writing that many keys stretched the twist track in time on a few sword clips
        dmi = seq.get_editor_property('data_model_interface'); fr = dmi.get_frame_rate()
        nkeys = dmi.get_number_of_keys(); length = u.AnimationLibrary.get_sequence_length(seq)
        times = [min(length, k * fr.denominator / fr.numerator) for k in range(nkeys)]
        poses = [u.AnimPoseExtensions.get_anim_pose_at_time(seq, tk, opts) for tk in times]
        backup(path)
        ctrl = seq.get_editor_property('controller'); ctrl.open_bracket('V9 forearm twist', False); written = []
        try:
            for s, sd in spec['sides'].items():
                axis = sd['axis_l']; rel_h = tuple(sd['rel_hand'])
                rolls, prev = [], None
                for pose in poses:
                    qL = qt(u.AnimPoseExtensions.get_bone_pose(pose, 'lowerarm_' + s, u.AnimPoseSpaces.WORLD).rotation)
                    qH = qt(u.AnimPoseExtensions.get_bone_pose(pose, 'hand_' + s, u.AnimPoseSpaces.WORLD).rotation)
                    r = twist(qmul(qmul(qinv(qL), qH), qinv(rel_h)), axis)
                    if prev is not None:
                        while r - prev > 180: r -= 360
                        while r - prev < -180: r += 360
                    rolls.append(r); prev = r
                # isolated spikes (evaluation glitches) are replaced by their neighbours' mean
                for k in range(len(rolls)):
                    nb = [rolls[j] for j in (k - 2, k - 1, k + 1, k + 2) if 0 <= j < len(rolls)]
                    med = sorted(nb)[len(nb) // 2] if nb else rolls[k]
                    if nb and abs(rolls[k] - med) > 30: rolls[k] = sum(nb) / len(nb)
                for bone, rel, share in (('lowerarm_twist_01_' + s, sd['rel_t1'], spec['shares'][0]), ('lowerarm_twist_02_' + s, sd['rel_t2'], spec['shares'][1])):
                    pos = [u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL).translation for pose in poses]
                    rot = [u.Quat(*qmul(qaxis(axis, share * r), tuple(rel))) for r in rolls]
                    scl = [u.Vector(1, 1, 1)] * nkeys
                    if not ctrl.set_bone_track_keys(bone, pos, rot, scl, False):
                        ctrl.add_bone_curve(bone, False)
                        if not ctrl.set_bone_track_keys(bone, pos, rot, scl, False): raise RuntimeError('cannot write ' + bone)
                    written.append(bone)
        finally:
            ctrl.close_bracket(False)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq): raise RuntimeError('finalize')
        E.set_metadata_tag(seq, TAG, '20261017 forearm twist: twist_01 100%% / twist_02 50%% of hand roll (%s)' % ','.join(spec['sides']))
        if not E.save_loaded_asset(seq, False): raise RuntimeError('save')
        row = dict(path=path, saved=True, keys=nkeys, bones=written, sha_before=before, sha256=sha(f))
    except Exception as e:
        row = dict(path=path, error=str(e))
    if row.get('saved'): rec.write_text(json.dumps(row, indent=1))
    else: (DONE_A / (rec.stem + '.failed.json')).write_text(json.dumps(row, indent=1))
    print('V9R_ANIM', json.dumps(row), flush=True)
print('V9R_INSTALL_COMPLETE', flush=True)
