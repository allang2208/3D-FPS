"""Read-only: verify the endpoint assumptions the M870 loader authoring relies on."""
import json
from pathlib import Path
import numpy as np
from rig import fk, inv

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
S, M = D['super90'], D['m870']; SC, MC = D['super90_clips'], D['m870_clips']


def world(sk, row): return fk(sk['names'], sk['parents'], row)


def pose_diff(a, b, bones):
    out = []
    for n in bones:
        dt = np.linalg.norm(a[n][:3, 3] - b[n][:3, 3])
        ra, rb = a[n][:3, :3] / np.linalg.norm(a[n][:3, :3], axis=0), b[n][:3, :3] / np.linalg.norm(b[n][:3, :3], axis=0)
        ang = np.degrees(np.arccos(np.clip((np.trace(ra.T @ rb) - 1) / 2, -1, 1)))
        if dt > .05 or ang > .2: out.append((n, round(float(dt), 2), round(float(ang), 2)))
    return out


names = S['names']
s_idle = world(S, SC['idle']['rows'][0]); m_idle = world(M, MC['idle']['rows'][0])
print('m870 idle vs super90 idle (cm, deg):', pose_diff(m_idle, s_idle, names))
for role in ('normal_1', 'normal_7', 'empty_7'):
    rows = SC[role]['rows']
    print(role, 'frame0 vs s90 idle:', pose_diff(world(S, rows[0]), s_idle, names)[:12])
    print(role, 'last vs s90 idle:', pose_diff(world(S, rows[-1]), s_idle, names)[:12])
cyc = MC['cycle']['rows']
print('m870 cycle frame0 vs m870 idle:', pose_diff(world(M, cyc[0]), m_idle, names)[:12])
print('m870 cycle last vs m870 idle:', pose_diff(world(M, cyc[-1]), m_idle, names)[:12])
for f in (0, 60, 100, 124, 130):
    print('normal_7 vs empty_7 frame', f, pose_diff(world(S, SC['normal_7']['rows'][f]), world(S, SC['empty_7']['rows'][f]), names)[:8])
for f in (60, 87, 100, 110):
    print('normal_1 vs normal_7 frame', f, pose_diff(world(S, SC['normal_1']['rows'][f]), world(S, SC['normal_7']['rows'][f]), names)[:8])
# Cycle: left hand relative to the pump (WPN_bolt) and pump travel.
for f in (0, 8, 16, 24, 32, 40, 48, 64):
    w = world(M, cyc[f]); r = w['WPN_root']
    print('cycle f%2d bolt %s hand_l %s hand_l-in-bolt %s root %s' % (f, (inv(r) @ w['WPN_bolt'])[:3, 3].round(3), (inv(r) @ w['hand_l'])[:3, 3].round(3),
          (inv(w['WPN_bolt']) @ w['hand_l'])[:3, 3].round(3), r[:3, 3].round(1)))
print('super90 empty_7 frames 124..224 left hand in gun:')
for f in (124, 140, 160, 174, 200, 224):
    w = world(S, SC['empty_7']['rows'][f]); r = w['WPN_root']; print('  ', f, (inv(r) @ w['hand_l'])[:3, 3].round(3), 'root', r[:3, 3].round(1))
for f in (124, 130, 136, 140, 144):
    w = world(S, SC['normal_7']['rows'][f]); r = w['WPN_root']; print(' normal_7', f, 'hand_l in gun', (inv(r) @ w['hand_l'])[:3, 3].round(3), 'root', r[:3, 3].round(1))
