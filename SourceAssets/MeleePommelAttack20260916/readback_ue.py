"""UE-side read-back check of the re-imported pommel clip (headless commandlet).

Confirms the asset that the game will actually load carries the fixed recover
tail: per-frame rotation deltas of the arm bones at 480 Hz over the last 0.22 s
of the clip, plus the clip length and skeleton.

Run through the ImportHost project so no editor session is needed:
    UnrealEditor-Cmd.exe <ImportHost.uproject> -run=pythonscript -script=...
Read-only.
"""
import json

import unreal as u

D = '/Game/Weapons/AzureRunesword20260913'
CLIP = D + '/A_RuneSword_PommelStrike'
OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\ue_readback.json"
HZ = 480.0
DT = 1.0 / HZ

anim = u.load_asset(CLIP)
if not anim:
    raise RuntimeError('clip missing: ' + CLIP)

BONES = ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']
length = float(anim.get_play_length())


def sample(bone, t):
    try:
        return u.AnimationLibrary.get_bone_pose_for_time(anim, bone, t, False)
    except Exception:
        return None


res = {'clip': CLIP, 'length': round(length, 4),
       'skeleton': anim.get_editor_property('skeleton').get_name() if anim.get_editor_property('skeleton') else None,
       'bones': {}}

import math


def ang_deg(pa, pb):
    d = abs(pa.w * pb.w + pa.x * pb.x + pa.y * pb.y + pa.z * pb.z)
    d = max(-1.0, min(1.0, d))
    return math.degrees(2.0 * math.acos(d))


for b in BONES:
    rows = []
    prev = None
    t = max(0.0, length - 0.22)
    while t <= length + 1e-9:
        tt = min(t, length)
        p = sample(b, tt)
        if p is None:
            break
        d = 0.0
        if prev is not None:
            d = ang_deg(prev.rotation, p.rotation)
        rows.append([round(tt, 4), round(d, 3)])
        prev = p
        t += DT
    if rows:
        res['bones'][b] = {'max': max(r[1] for r in rows),
                           'last': rows[-1][1],
                           'peak_at': max(rows, key=lambda r: r[1])[0]}

# Endpoint continuity: the game hands the pose back to A_RuneSword_Idle by
# sampling its frame 0, so the clip's first and last frame must match it.
idle = u.load_asset(D + '/A_RuneSword_Idle')
if idle:
    check = {}
    for b in ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']:
        pf = sample(b, 0.0)
        pl = sample(b, length)
        pi = u.AnimationLibrary.get_bone_pose_for_time(idle, b, 0.0, False)
        if pf is None or pl is None or pi is None:
            continue
        check[b] = {
            'start_vs_idle_cm': round((pf.translation - pi.translation).length() * 100, 5),
            'end_vs_idle_cm': round((pl.translation - pi.translation).length() * 100, 5),
            'end_vs_idle_deg': round(ang_deg(pl.rotation, pi.rotation), 5),
        }
    res['endpoint_check'] = check
    u.log('POMMEL_ENDPOINTS ' + ' '.join('%s end=%.5fcm/%.5fdeg' % (b, v['end_vs_idle_cm'], v['end_vs_idle_deg']) for b, v in check.items()))

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
u.log('POMMEL_READBACK_DONE length=%.4f' % length)
for b, v in res['bones'].items():
    u.log('POMMEL_TAIL %s max=%.3f last=%.3f at=%.3f' % (b, v['max'], v['last'], v['peak_at']))
print('WROTE', OUT)