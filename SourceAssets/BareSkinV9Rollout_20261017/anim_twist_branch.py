"""Commandlet: forearm twist branch repair on the clips written by anim_fix_raw.py (data model, every key).

anim_fix_raw unwrapped the hand roll continuously from key 0. A non-physical jump between two keys (> 180 deg)
can leave the rest of the clip on the +-360 branch: twist_01 (100 %) looks the same, but twist_02 (50 %) is
then 180 deg off - a candy-wrapped mid forearm. Here the roll is unwrapped, shifted by the multiple of 360 that
centres it on 0, and any key still beyond +-210 deg is folded back, so twist_02 stays within about +-105 deg.
Only sides whose written twist_02 differs from that by > 3 deg are rewritten (twist_01 / 02 keys only; the
hand's roll relative to lowerarm is the hand's local rotation, the twist bones are leaves of lowerarm).
Receipts: InstalledBranch/<hash>.json."""
import json, os, sys, math, hashlib, gc
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
E = u.EditorAssetLibrary; DONE = R / 'InstalledBranch'; DONE.mkdir(exist_ok=True)
FOLD, TOL = 210.0, 3.0
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def disk(path): return P / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def qt(q): return (q.x, q.y, q.z, q.w)


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


def wrap(d): return (d + 180.0) % 360.0 - 180.0


def branch(rolls):
    un, prev = [], None
    for r in rolls:
        if prev is not None:
            while r - prev > 180: r -= 360
            while r - prev < -180: r += 360
        un.append(r); prev = r
    k = round(sum(un) / len(un) / 360.0); un = [x - 360.0 * k for x in un]
    return [x - 360.0 if x > FOLD else x + 360.0 if x < -FOLD else x for x in un]


rec_by_path = {}
for f in (R / 'InstalledRaw').glob('*.json'):
    if f.stem.endswith('.failed'): continue
    d = json.loads(f.read_text())
    if d.get('twist'): rec_by_path[d['path']] = d
specs = {}
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    sf = R / 'Work' / b / 'twist_specs.json'
    if sf.exists():
        for path, s in json.loads(sf.read_text()).items(): specs.setdefault(path, s)
HIER = json.loads((R / 'Work/mesh_hierarchy.json').read_text())
count = 0; meshes = {}
for path, rr in sorted(rec_by_path.items()):
    rec = DONE / (hashlib.sha256(path.encode()).hexdigest()[:12] + '.json')
    if rec.exists(): continue
    spec = specs.get(path)
    try:
        if not spec: raise RuntimeError('no twist spec')
        if path in dirty: raise RuntimeError('package dirty')
        f = disk(path)
        if sha(f) != rr['sha256']: raise RuntimeError('asset changed since the data-model pass')
        seq = u.load_asset(path + '.' + path.split('/')[-1])
        dmi = seq.get_editor_property('data_model_interface'); n = dmi.get_number_of_keys()
        vm = spec['mesh']; par = dict(zip(HIER[vm]['names'], HIER[vm]['parents']))
        sides = [s for s in spec['sides'] if 'lowerarm_twist_02_' + s in rr['twist']]
        for s in sides:
            if any(par.get(x + s) != 'lowerarm_' + s for x in ('hand_', 'lowerarm_twist_01_', 'lowerarm_twist_02_')): raise RuntimeError('hierarchy: not children of lowerarm_' + s)
        meshes.setdefault(vm, u.load_asset(vm + '.' + vm.split('/')[-1]))
        names = [x for s in sides for x in ('hand_' + s, 'lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s)]
        locs = [dict(zip(names, u.AnimationLibrary.get_bone_poses_for_frame(seq, names, k, False, meshes[vm]))) for k in range(n)]
        writes = {}; info = {}
        for s in sides:
            sd = spec['sides'][s]; axis = sd['axis_l']; rel_h = tuple(sd['rel_hand']); rel_t2 = tuple(sd['rel_t2'])
            rolls = [twist(qmul(qt(l['hand_' + s].rotation), qinv(rel_h)), axis) for l in locs]
            new = branch(rolls)
            cur2 = [twist(qmul(qt(l['lowerarm_twist_02_' + s].rotation), qinv(rel_t2)), axis) for l in locs]
            err = [abs(wrap(c - spec['shares'][1] * r)) for c, r in zip(cur2, new)]
            info[s] = dict(max_err=round(max(err), 2), keys_off=sum(e > TOL for e in err), roll_range=[round(min(new), 1), round(max(new), 1)])
            if max(err) <= TOL: continue
            for bone, rel, share in (('lowerarm_twist_01_' + s, sd['rel_t1'], spec['shares'][0]), ('lowerarm_twist_02_' + s, sd['rel_t2'], spec['shares'][1])):
                pos = [l[bone].translation for l in locs]
                rot = [u.Quat(*qmul(qaxis(axis, share * r), tuple(rel))) for r in new]
                writes[bone] = (pos, rot, [u.Vector(1, 1, 1)] * n)
        if writes:
            before = sha(f); ctrl = seq.get_editor_property('controller'); ctrl.open_bracket('V9 forearm twist branch', False)
            try:
                for bone, (pos, rot, scl) in writes.items():
                    if not ctrl.set_bone_track_keys(bone, pos, rot, scl, False): raise RuntimeError('cannot write ' + bone)
            finally:
                ctrl.close_bracket(False)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq): raise RuntimeError('finalize')
            E.set_metadata_tag(seq, 'BareSkinV9Branch', '20261018 forearm twist branch centred (%s)' % ','.join(sorted(writes)))
            if not E.save_loaded_asset(seq, False): raise RuntimeError('save')
            row = dict(path=path, keys=n, rewritten=sorted(writes), sides=info, sha_before=before, sha256=sha(f))
            print('V9R_BRANCH', json.dumps(dict(path=path, sides=info)), flush=True)
        else:
            row = dict(path=path, keys=n, rewritten=[], sides=info)
        rec.write_text(json.dumps(row, indent=1))
    except Exception as e:
        (DONE / (rec.stem + '.failed.json')).write_text(json.dumps(dict(path=path, error=str(e))))
        print('V9R_BRANCH_FAIL', path, str(e), flush=True)
    count += 1; locs = None
    if count % 25 == 0: gc.collect(); u.SystemLibrary.collect_garbage()
print('V9R_BRANCH_COMPLETE', count, flush=True)
