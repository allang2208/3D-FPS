"""Preview poses for the hatchet pairs and the lone off-hand blade (2026-11-04) -> Work/previews_<set>.json, rendered by
render_pair_preview.py (Blender, V7 editable arms, real SM_TacticalHatchet / SM_Kukri), sheets in Previews/.

Sets:
  pairs  DualEquip, PairEquipHK, PairEquipKH (1/30 s) and PairAttack3HK, PairAttack3KH (1/20 s): each hand with its own
         weapon; the left weapon rides hand_l through the clip's own relation (the 60 Hz draw tables, else the constant grip).
  lone   main hand empty, off-hand hatchet: HatchetEquip (1/30 s), Attack and HatchetAttack3 (1/20 s) mirrored onto the left
         arm exactly as UKukriArmsMeshComponent does it (MirrorRightPose: mirrored world rotation * bind correction, the
         left bones' own bind translations, the clavicle at the mirrored position + the bind offset; the blade = the grip-locked
         right relation mirrored through hand_l's bind correction).  The right arm is masked out (bLeftHandOnly).
No authored camera motion is applied (the viewmodel is shown in its own frame).
Run:  python -I preview_pairs.py [pairs] [lone] [--render]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
DUAL = P.parent / 'DualKukriIdle20261025'
sys.path.insert(0, str(DUAL))
sys.path.insert(0, str(P))
from dual_rig import DualRig  # noqa: E402
from kmath import T, qmat, qfrommat, qslerp  # noqa: E402
import author_pairs as A  # noqa: E402

FPS = 120
WORK = P / 'Work'
PREVIEWS = P / 'Previews'
BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
F = np.diag([-1.0, 1.0, 1.0])
RZ = np.diag([-1.0, -1.0, 1.0])
HOLD_BAND, RELEASE_BAND, DEG_TO_CM = 0.6, 2.5, 0.25
KUKRI_CLIPS = P.parent / 'Kukri20261020' / 'Clips'
HATCHET_EQUIP = P.parent / 'HatchetEquip20261101' / 'Clips' / 'HatchetEquip.json'
HATCHET_CHOP = P.parent / 'HatchetChop20261102' / 'Clips' / 'HatchetAttack3.json'


def unit(x):
    return T(x.p, x.q, (1, 1, 1))


def frame_world(rig, clip, i):
    fr = clip['frames'][min(i, len(clip['frames']) - 1)]
    return rig.world({b: T(v[0], v[1], v[2]) for b, v in fr.items()})


def pose_entry(world, right=None, right_kind=None, left=None, left_kind=None, hide_right=False):
    out = dict(bones={b: x.pack() for b, x in world.items()}, hide_right=hide_right)
    if right is not None:
        out['weapon_r'] = right.pack(); out['weapon_r_kind'] = right_kind
    if left is not None:
        out['weapon_l'] = left.pack(); out['weapon_l_kind'] = left_kind
    return out


# ---------------------------------------------------------------- pairs
def pairs(D):
    rig = D.R.rig
    grip = A.left_grip()
    kukri_rows = A.load(DUAL / 'Work' / 'dual_equip_left.json')['rows']
    hatchet_rows = A.author_dual_equip(D)[1]
    rel = dict(kukri=lambda t: A.table_sample(kukri_rows, t),
               hatchet=lambda t: A.table_sample([(t_, q, p) for t_, q, p in hatchet_rows], t),
               grip=lambda t: grip)
    clips = [('DualEquip', 'hatchet', 'hatchet', 'hatchet', 30), ('PairEquipHK', 'hatchet', 'kukri', 'kukri', 30),
             ('PairEquipKH', 'kukri', 'hatchet', 'hatchet', 30), ('PairAttack3HK', 'hatchet', 'kukri', 'grip', 20),
             ('PairAttack3KH', 'kukri', 'hatchet', 'grip', 20)]
    poses = {}
    for name, rk, lk, table, hz in clips:
        clip = A.load(A.OUT / (name + '.json'))
        n = int(round(clip['length'] * hz))
        for k in range(n + 1):
            t = k / hz
            world = frame_world(rig, clip, int(round(t * FPS)))
            right = unit(world['WPN_root'])
            left = rel[table](t) * unit(world['hand_l'])
            poses['%s_%04d' % (name, int(round(t * 1000)))] = pose_entry(world, right, rk, left, lk)
    return poses


def dash(D):
    """The pair's sprint attack (DualSprintAttack20261104), both hands chopping down: hatchet pair and kukri pair, 1/30 s."""
    rig = D.R.rig
    grip = A.left_grip()
    clip = A.load(P.parent / 'DualSprintAttack20261104' / 'Clips' / 'DualSprintAttack.json')
    poses = {}
    for name, kind in (('DualSprintAttackHH', 'hatchet'), ('DualSprintAttackKK', 'kukri')):
        n = int(round(clip['length'] * 30))
        for k in range(n + 1):
            t = k / 30.0
            world = frame_world(rig, clip, int(round(t * FPS)))
            poses['%s_%04d' % (name, int(round(t * 1000)))] = pose_entry(world, unit(world['WPN_root']), kind,
                                                                          grip * unit(world['hand_l']), kind)
    return poses


# ---------------------------------------------------------------- lone off-hand (runtime mirror)
class LoneMirror:
    def __init__(self, D):
        R = D.R
        self.R, self.rig = R, R.rig
        bind = R.ref_world
        self.left = [n for n in R.rig.names if n in R.left_chain]
        self.src = {n: n[:-2] + '_r' for n in self.left if n.endswith('_l') and n[:-2] + '_r' in bind}
        self.corr = {n: (F @ qmat(bind[self.src[n]].q) @ F).T @ qmat(bind[n].q) for n in self.src}
        self.offset = bind['clavicle_l'].p - F @ bind['clavicle_r'].p
        self.parent = dict(zip(R.rig.names, R.rig.parents))

    def mirror(self, world):
        """UKukriArmsMeshComponent::MirrorRightPose on a component-space (mesh) pose."""
        out = dict(world)
        ref = self.R.ref_local
        for n in self.left:
            if n not in self.src:
                continue
            r = world[self.src[n]]
            goal = F @ qmat(r.q) @ F @ self.corr[n]
            par = out[self.parent[n]]
            if n == 'clavicle_l':
                p = F @ r.p + self.offset
            else:
                p = par.point(ref[n].p)
            out[n] = T(p, qfrommat(goal), ref[n].s * par.s)
        return out

    def blade(self, world, mirrored):
        """The lone blade: the grip-locked right relation mirrored into hand_l (runtime formula)."""
        R = self.R
        hr = world['hand_r']
        clip = unit(world['WPN_root'])
        lock = unit(R.hand_rel.inverse() * hr)
        dev = float(np.linalg.norm(clip.p - lock.p)) + np.degrees(2 * np.arccos(min(1.0, abs(float(np.dot(clip.q, lock.q)))))) * DEG_TO_CM
        free = A.smooth(HOLD_BAND, RELEASE_BAND, dev)
        held = A.blend_t(lock, clip, free)
        q_rel = qmat(hr.q).T @ qmat(held.q)
        l_rel = qmat(hr.q).T @ (held.p - hr.p)
        c = self.corr['hand_l']
        hl = mirrored['hand_l']
        rot = qmat(hl.q) @ (c.T @ (F @ q_rel @ F) @ RZ)
        pos = hl.p + qmat(hl.q) @ (c.T @ (F @ l_rel))
        return T(pos, qfrommat(rot), (1, 1, 1))


def lone(D):
    M = LoneMirror(D)
    rig = D.R.rig
    clips = [('LoneHatchetEquip', HATCHET_EQUIP, 30), ('LoneAttack', KUKRI_CLIPS / 'Attack.json', 20),
             ('LoneHatchetAttack3', HATCHET_CHOP, 20)]
    poses = {}
    for name, path, hz in clips:
        clip = A.load(path)
        n = int(round(clip['length'] * hz))
        for k in range(n + 1):
            t = k / hz
            world = frame_world(rig, clip, int(round(t * FPS)))
            mirrored = M.mirror(world)
            poses['%s_%04d' % (name, int(round(t * 1000)))] = pose_entry(mirrored, left=M.blade(world, mirrored),
                                                                          left_kind='hatchet', hide_right=True)
    return poses


# ---------------------------------------------------------------- render + sheets
def render(set_name, poses, width=960):
    import cv2
    frames = WORK / ('frames_' + set_name)
    frames.mkdir(parents=True, exist_ok=True)
    for old in frames.glob('*.png'):
        old.unlink()
    pj = WORK / ('previews_%s.json' % set_name)
    pj.write_text(json.dumps(dict(poses=poses)), encoding='utf-8')
    res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_pair_preview.py'), '--', str(pj),
                          str(frames), str(width)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or 'Traceback' in res.stdout or 'Traceback' in res.stderr:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise RuntimeError('preview render failed')
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    groups = {}
    for name in sorted(poses):
        groups.setdefault(name.rsplit('_', 1)[0], []).append(name)
    for clip, names in groups.items():
        cells = []
        for name in names:
            im = cv2.imread(str(frames / (name + '.png')))
            im = cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA)
            cv2.putText(im, '%s  %.3f s' % (clip, int(name.rsplit('_', 1)[1]) / 1000.0), (8, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        .5, (255, 255, 255), 1, cv2.LINE_AA)
            cells.append(im)
        while len(cells) % 4:
            cells.append(np.zeros_like(cells[0]))
        rows = [np.hstack(cells[k:k + 4]) for k in range(0, len(cells), 4)]
        for s in range(0, len(rows), 4):
            out = PREVIEWS / ('%s_sheet_%d.jpg' % (clip, s // 4))
            cv2.imwrite(str(out), np.vstack(rows[s:s + 4]), [cv2.IMWRITE_JPEG_QUALITY, 82])
        print('%-20s %d frames -> %s_sheet_*.jpg' % (clip, len(names), clip), flush=True)


def main():
    sets = [a for a in sys.argv[1:] if not a.startswith('--')] or ['pairs', 'lone']
    D = DualRig()
    for s in sets:
        poses = pairs(D) if s == 'pairs' else dash(D) if s == 'dash' else lone(D)
        print(s, len(poses), 'poses', flush=True)
        if '--render' in sys.argv:
            render(s, poses)
        else:
            (WORK / ('previews_%s.json' % s)).write_text(json.dumps(dict(poses=poses)), encoding='utf-8')


if __name__ == '__main__':
    main()
