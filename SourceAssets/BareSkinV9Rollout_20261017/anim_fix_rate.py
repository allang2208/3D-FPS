"""Commandlet: redo the data-model pass on the clips whose sampling frame rate differs from the data-model rate
(Work/rate_mismatch.json). get_bone_poses_for_frame(k) maps k with the sampling rate there, so anim_fix_raw read
the wrong times (a 240 vs 120 fps clip: the first half, stretched). Here every key k is read at k / model rate
(get_bone_poses_for_time), then the same bad-key repair and the forearm twist with the centred branch
(anim_twist_branch.branch) are written. Clips that had arm tracks rewritten by anim_fix_raw were restored from
Before/ first (restore_rate.py). Receipts: InstalledRate/<hash>.json."""
import json, sys, math, hashlib, shutil, gc
from pathlib import Path
sys.path.insert(0, 'D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
E = u.EditorAssetLibrary; DONE = R / 'InstalledRate'; DONE.mkdir(exist_ok=True)
HIER = json.loads((R / 'Work/mesh_hierarchy.json').read_text()); REFS = json.loads((R / 'Work/mesh_ref_local.json').read_text())
JUMP, AGREE, NEAR, FAR, RUN_AGREE, FOLD = 25.0, 10.0, 3.0, 20.0, 15.0, 210.0
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def disk(path): return P / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def qt(q): return (q.x, q.y, q.z, q.w)


def ang(a, b):
    d = abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w); return math.degrees(2 * math.acos(min(1.0, d)))


def slerp(a, b, t):
    d = a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w
    if d < 0: b = u.Quat(-b.x, -b.y, -b.z, -b.w); d = -d
    if d > .9995: q = u.Quat(a.x + t * (b.x - a.x), a.y + t * (b.y - a.y), a.z + t * (b.z - a.z), a.w + t * (b.w - a.w))
    else:
        th = math.acos(d); s = math.sin(th); wa = math.sin((1 - t) * th) / s; wb = math.sin(t * th) / s
        q = u.Quat(wa * a.x + wb * b.x, wa * a.y + wb * b.y, wa * a.z + wb * b.z, wa * a.w + wb * b.w)
    n = math.sqrt(q.x ** 2 + q.y ** 2 + q.z ** 2 + q.w ** 2); return u.Quat(q.x / n, q.y / n, q.z / n, q.w / n)


def lerpv(a, b, t): return u.Vector(a.x + t * (b.x - a.x), a.y + t * (b.y - a.y), a.z + t * (b.z - a.z))


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


def branch(rolls):
    un, prev = [], None
    for r in rolls:
        if prev is not None:
            while r - prev > 180: r -= 360
            while r - prev < -180: r += 360
        un.append(r); prev = r
    k = round(sum(un) / len(un) / 360.0); un = [x - 360.0 * k for x in un]
    return [x - 360.0 if x > FOLD else x + 360.0 if x < -FOLD else x for x in un]


def bad_keys(q, ref, cap):
    n = len(q); out = []
    for k in range(1, n - 1):
        if ang(q[k], q[k - 1]) > JUMP and ang(q[k], q[k + 1]) > JUMP and ang(q[k - 1], q[k + 1]) < AGREE: out.append([k, k + 1])
    if ref is not None:
        near = [ang(x, ref) < NEAR for x in q]; k = 0
        while k < n:
            if not near[k]: k += 1; continue
            a = k
            while k < n and near[k]: k += 1
            b = k
            if b - a > cap: continue
            L = q[a - 1] if a > 0 else None; Rr = q[b] if b < n else None
            if L is None and Rr is None: continue
            ok = all(ang(x, ref) > FAR for x in (L, Rr) if x is not None)
            if L is not None and Rr is not None: ok = ok and ang(L, Rr) < RUN_AGREE
            if ok and [a, b] not in out: out.append([a, b])
    return out


def repair(arr, rng):
    pos, rot, scl = arr; n = len(rot)
    for a, b in rng:
        for k in range(a, b):
            if a == 0: rot[k] = rot[b]; pos[k] = pos[b]; scl[k] = scl[b]
            elif b == n: rot[k] = rot[a - 1]; pos[k] = pos[a - 1]; scl[k] = scl[a - 1]
            else:
                t = (k - a + 1) / (b - a + 1); rot[k] = slerp(rot[a - 1], rot[b], t); pos[k] = lerpv(pos[a - 1], pos[b], t)


raw = {}
for f in (R / 'InstalledRaw').glob('*.json'):
    if not f.stem.endswith('.failed'): d = json.loads(f.read_text()); raw[d['path']] = d
specs = {}
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    sf = R / 'Work' / b / 'twist_specs.json'
    if sf.exists():
        for path, s in json.loads(sf.read_text()).items(): specs.setdefault(path, s)
jobs = json.loads((R / 'Work/rate_mismatch.json').read_text())
meshes = {}
for job in jobs:
    path = job['path']; rec = DONE / (hashlib.sha256(path.encode()).hexdigest()[:12] + '.json')
    if rec.exists(): continue
    try:
        if path in dirty: raise RuntimeError('package dirty')
        rr = raw.get(path) or {}; spec = specs.get(path)
        vm = (spec or {}).get('mesh') or rr.get('mesh')
        if not vm:
            # same viewmodel the data-model pass used: first batch plan listing a clip file that holds the path
            for b in ('batch1', 'batch2', 'batch3', 'batch4'):
                plan = json.loads((R / (b + '.json')).read_text())
                for name, v in plan['viewmodels'].items():
                    cf = R / 'Clips' / (name + '.json')
                    if cf.exists() and path in json.loads(cf.read_text())['clips']: vm = v; break
                if vm: break
        if not vm: raise RuntimeError('no viewmodel')
        seq = u.load_asset(path + '.' + path.split('/')[-1]); f = disk(path)
        meshes.setdefault(vm, u.load_asset(vm + '.' + vm.split('/')[-1])); mesh = meshes[vm]
        dmi = seq.get_editor_property('data_model_interface'); n = dmi.get_number_of_keys(); fr = dmi.get_frame_rate(); rate = fr.numerator / fr.denominator
        cap = max(2, int(round(rate / 4)))
        names = HIER[vm]['names']
        arm = [x for x in names if x.endswith(('_l', '_r')) and not x.startswith('ik_') and
               any(t in x for t in ('clavicle', 'upperarm', 'lowerarm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky'))]
        locs = [dict(zip(names, u.AnimationLibrary.get_bone_poses_for_time(seq, names, k / rate, False, mesh))) for k in range(n)]
        tracks = set(str(x) for x in dmi.get_bone_track_names()); arrays = {}

        def arr(b):
            if b not in arrays: arrays[b] = ([l[b].translation for l in locs], [l[b].rotation for l in locs], [l[b].scale3d for l in locs])
            return arrays[b]
        fixed = {}
        if n >= 4:
            for b in arm:
                if b not in tracks or 'twist' in b: continue
                rq = REFS[vm].get(b); ref = u.Quat(*rq) if rq else None
                rng = bad_keys(arr(b)[1], ref, cap)
                if rng: repair(arr(b), rng); fixed[b] = rng
        written = []
        if spec:
            par = dict(zip(names, HIER[vm]['parents']))
            for s, sd in spec['sides'].items():
                if par.get('hand_' + s) != 'lowerarm_' + s: raise RuntimeError('hierarchy')
                axis = sd['axis_l']; rel_h = tuple(sd['rel_hand'])
                hq = arrays['hand_' + s][1] if 'hand_' + s in arrays else [l['hand_' + s].rotation for l in locs]
                rolls = branch([twist(qmul(qt(q), qinv(rel_h)), axis) for q in hq])
                for bone, rel, share in (('lowerarm_twist_01_' + s, sd['rel_t1'], spec['shares'][0]), ('lowerarm_twist_02_' + s, sd['rel_t2'], spec['shares'][1])):
                    if bone not in names: continue
                    arrays[bone] = ([l[bone].translation for l in locs], [u.Quat(*qmul(qaxis(axis, share * r), tuple(rel))) for r in rolls], [u.Vector(1, 1, 1)] * n)
                    written.append(bone)
        changed = list(fixed) + written
        if changed:
            b_ = R / 'Before' / f.relative_to(P); b_.parent.mkdir(parents=True, exist_ok=True)
            if not b_.exists(): shutil.copy2(f, b_)
            before = sha(f); ctrl = seq.get_editor_property('controller'); ctrl.open_bracket('V9 arms: model-rate pass', False)
            try:
                for b in changed:
                    pos, rot, scl = arrays[b]
                    if not ctrl.set_bone_track_keys(b, pos, rot, scl, False):
                        ctrl.add_bone_curve(b, False)
                        if not ctrl.set_bone_track_keys(b, pos, rot, scl, False): raise RuntimeError('cannot write ' + b)
            finally:
                ctrl.close_bracket(False)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq): raise RuntimeError('finalize')
            E.set_metadata_tag(seq, 'BareSkinV9', '20261018 model-rate pass: bad keys %s; forearm twist 100/50 %s' % (','.join(fixed) or '-', ','.join(written) or '-'))
            if not E.save_loaded_asset(seq, False): raise RuntimeError('save')
            # readback at the same model-rate times
            chk = [dict(zip(changed, u.AnimationLibrary.get_bone_poses_for_time(seq, changed, k / rate, False, mesh))) for k in range(0, n, max(1, n // 12))]
            err = max(ang(c[b].rotation, arrays[b][1][k * max(1, n // 12)]) for i, c in enumerate(chk) for k in [i] for b in changed)
            row = dict(path=path, keys=n, model_rate=rate, fixed=fixed, twist=written, readback_max_deg=round(err, 4), sha_before=before, sha256=sha(f))
        else:
            row = dict(path=path, keys=n, model_rate=rate, fixed={}, twist=[])
        rec.write_text(json.dumps(row, indent=1)); print('V9R_RATEFIX', json.dumps(dict(path=path, fixed=list(fixed), twist=len(written), readback=row.get('readback_max_deg'))), flush=True)
    except Exception as e:
        (DONE / (rec.stem + '.failed.json')).write_text(json.dumps(dict(path=path, error=str(e))))
        print('V9R_RATEFIX_FAIL', path, str(e), flush=True)
    locs = None; arrays = None; gc.collect()
print('V9R_RATEFIX_COMPLETE', len(jobs), flush=True)
