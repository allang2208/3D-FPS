"""Author-side checks of clips.json (no UE): endpoints, joins, contact, continuity, loader seat."""
import json
from pathlib import Path
import numpy as np
from rig import fk, inv

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text()); C = json.loads((O / 'clips.json').read_text())
M, S = D['m870'], D['super90']; NAMES, PAR = M['names'], M['parents']
W_MIDLE = fk(NAMES, PAR, D['m870_clips']['idle']['rows'][0])
G_R = inv(W_MIDLE['WPN_root']) @ W_MIDLE['hand_r']; G_L = inv(W_MIDLE['WPN_root']) @ W_MIDLE['hand_l']


def ang(a, b):
    ra, rb = a[:3, :3] / np.linalg.norm(a[:3, :3], axis=0), b[:3, :3] / np.linalg.norm(b[:3, :3], axis=0)
    return float(np.degrees(np.arccos(np.clip((np.trace(ra.T @ rb) - 1) / 2, -1, 1))))


def maxdiff(Wa, Wb, bones):
    return max(np.linalg.norm(Wa[n][:3, 3] - Wb[n][:3, 3]) for n in bones), max(ang(Wa[n], Wb[n]) for n in bones)


report = {}
for role, clip in C.items():
    rows = clip['rows']; Ws = [fk(NAMES, PAR, r) for r in rows]
    r = {}
    r['start_vs_idle_cm_deg'] = [round(x, 3) for x in maxdiff(Ws[0], W_MIDLE, [n for n in NAMES if n not in ('WPN_Shell', 'WPN_SOCKET_Magazine')])]
    r['end_vs_idle_cm_deg'] = [round(x, 3) for x in maxdiff(Ws[-1], W_MIDLE, NAMES)]
    jumps = {}
    for b in ('hand_l', 'lowerarm_l', 'hand_r', 'lowerarm_r', 'WPN_root', 'WPN_Shell'):
        d = [np.linalg.norm(Ws[i + 1][b][:3, 3] - Ws[i][b][:3, 3]) for i in range(len(Ws) - 1)]
        a = [ang(Ws[i + 1][b], Ws[i][b]) for i in range(len(Ws) - 1)]
        jumps[b] = dict(max_cm=round(max(d), 2), at=int(np.argmax(d)), max_deg=round(max(a), 2), at_deg=int(np.argmax(a)))
    r['per_frame_max'] = jumps
    r['right_contact_err_cm'] = round(max(np.linalg.norm((W['WPN_root'] @ G_R)[:3, 3] - W['hand_r'][:3, 3]) for W in Ws), 4)
    mouth = inv(Ws[110]['WPN_root']) @ Ws[110]['WPN_Shell']; r['seat_tip_gun_m'] = mouth[:3, 3].round(4).tolist()
    src = D['super90_clips']['normal_' + role.split('_')[1]]['rows']
    rel = []
    for f in range(80, 116):
        Wsrc = fk(S['names'], S['parents'], src[f])
        a = inv(Wsrc['WPN_SOCKET_Magazine']) @ Wsrc['hand_l']; b = inv(Ws[f]['WPN_SOCKET_Magazine']) @ Ws[f]['hand_l']
        rel.append((np.linalg.norm(a[:3, 3] - b[:3, 3]), ang(a, b)))
    r['hand_vs_plunger_drift_cm_deg'] = [round(max(x[0] for x in rel), 3), round(max(x[1] for x in rel), 3)]
    if role.startswith('empty'):
        r['join_144_145_cm_deg'] = [round(x, 3) for x in maxdiff(Ws[144], Ws[145], [n for n in NAMES if n not in ('WPN_Shell', 'WPN_SOCKET_Magazine')])]
        r['frame144_vs_cycle0'] = [round(x, 3) for x in maxdiff(Ws[144], fk(NAMES, PAR, D['m870_clips']['cycle']['rows'][0]), NAMES)]
    report[role] = r
    print(role, json.dumps(r))
(O / 'clip_checks.json').write_text(json.dumps(report, indent=1))
