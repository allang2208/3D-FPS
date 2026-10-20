"""Commandlet: write the arm axial fix (Work/ArmPlan) - new local rotations of upperarm, lowerarm, hand and the two
forearm twist bones per changed side; translations and scales stay as in the data model. The asset must still be
what this rollout last wrote (latest receipt hash) and clean. Receipts: InstalledArm/<hash>.json."""
import json, sys, math, hashlib, shutil, gc
from pathlib import Path
import unreal as u

import os
P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
PLAN = R / os.environ.get('V9R_ARM_PLAN', 'Work/ArmPlan')                 # R3b: Work/ArmPlan2 -> InstalledArm2
E = u.EditorAssetLibrary; DONE = R / os.environ.get('V9R_ARM_DONE', 'InstalledArm'); DONE.mkdir(exist_ok=True)
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def disk(path): return P / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def ang(a, b):
    d = abs(a.x * b[0] + a.y * b[1] + a.z * b[2] + a.w * b[3]); return math.degrees(2 * math.acos(min(1.0, d)))


latest = {}
for d in ('InstalledRaw', 'InstalledBranch', 'InstalledRate', 'InstalledArm', 'InstalledArm2', 'InstalledArm3'):    # later wins
    if not (R / d).exists(): continue
    for f in (R / d).glob('*.json'):
        if f.stem.endswith('.failed'): continue
        r = json.loads(f.read_text())
        if r.get('sha256') and (r.get('twist') or r.get('fixed') or r.get('rewritten') or r.get('bones')): latest[r['path']] = r['sha256']
for f in sorted(PLAN.glob('*.json')):
    rec = DONE / f.name
    if rec.exists(): continue
    plan = json.loads(f.read_text()); path = plan['path']
    try:
        if path in dirty: raise RuntimeError('package dirty')
        fd = disk(path); now = sha(fd)
        if path in latest and now != latest[path]: raise RuntimeError('asset changed since the last rollout write')
        b_ = R / 'Before' / fd.relative_to(P); b_.parent.mkdir(parents=True, exist_ok=True)
        if not b_.exists(): shutil.copy2(fd, b_)
        seq = u.load_asset(path + '.' + path.split('/')[-1])
        n = seq.get_editor_property('data_model_interface').get_number_of_keys()
        if n != plan['n']: raise RuntimeError('key count changed %d -> %d' % (plan['n'], n))
        bones = [b for s in plan['sides'].values() for b in s]; rots = {b: v for s in plan['sides'].values() for b, v in s.items()}
        cur = [u.AnimationLibrary.get_bone_poses_for_frame(seq, bones, k, False) for k in range(n)]
        ctrl = seq.get_editor_property('controller'); ctrl.open_bracket('V9 arm axial fix', False)
        try:
            for i, b in enumerate(bones):
                pos = [c[i].translation for c in cur]; scl = [c[i].scale3d for c in cur]; rot = [u.Quat(*q) for q in rots[b]]
                if not ctrl.set_bone_track_keys(b, pos, rot, scl, False):
                    ctrl.add_bone_curve(b, False)
                    if not ctrl.set_bone_track_keys(b, pos, rot, scl, False): raise RuntimeError('cannot write ' + b)
        finally:
            ctrl.close_bracket(False)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq): raise RuntimeError('finalize')
        E.set_metadata_tag(seq, 'BareSkinV9Arm', '20261018 arm axial fix (elbow hinge / hand roll re-route): %s' % ','.join(sorted(plan['sides'])))
        if not E.save_loaded_asset(seq, False): raise RuntimeError('save')
        err = 0.0
        for k in range(0, n, max(1, n // 10)):
            got = u.AnimationLibrary.get_bone_poses_for_frame(seq, bones, k, False)
            err = max(err, max(ang(g.rotation, rots[b][k]) for g, b in zip(got, bones)))
        row = dict(path=path, keys=n, bones=bones, info=plan.get('info'), readback_max_deg=round(err, 4), sha_before=now, sha256=sha(fd))
        rec.write_text(json.dumps(row, indent=1)); print('V9R_ARMFIX', json.dumps(dict(path=path, readback=row['readback_max_deg'])), flush=True)
    except Exception as e:
        (DONE / (f.stem + '.failed.json')).write_text(json.dumps(dict(path=path, error=str(e))))
        print('V9R_ARMFIX_FAIL', path, str(e), flush=True)
    cur = None; gc.collect()
print('V9R_ARMFIX_COMPLETE', flush=True)
