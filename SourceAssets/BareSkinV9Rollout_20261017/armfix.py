"""Arm axial fix per clip side (numpy / scipy; the offline check and the UE commandlet share it).

1. Elbow: keys whose forearm bone is rolled more than 60 deg inside the elbow (a hinge) move that roll into the
   forearm, fully at 120 deg (elbow_hinge.Side.blend_beta). Per key, so clips that blend into each other agree.
2. Hand roll beyond the anatomical range: re-route (reroute.plan_side, user approved 10-18).
Joint positions and (except a re-routed left hand) the hand's world rotation never change.
Returns per key: alpha (upper arm about shoulder->elbow), beta (forearm about elbow->wrist), gamma (hand about the
same line, negative = against p), p_final (hand roll for the twist bones, continuous, within +-P_MAX)."""
import math
import numpy as np
from scipy.spatial.transform import Rotation as Rot
import elbow_hinge as eh
import reroute as rr


def unit(v): return v / max(np.linalg.norm(v), 1e-12)


def plan(keys, ref, s, sd, rate, blend=True):
    side = eh.Side(ref, s, sd['rel_hand'], sd['axis_l'])
    beta1 = np.array([side.blend_beta(k['U'], k['L'], k['H'])[0] for k in keys]) if blend else np.zeros(len(keys))
    if blend and (np.abs(beta1) > .5).any():
        # continuity guard: where the elbow spins round quickly the per-key split jumps between keys; the forearm
        # twist would then pop. Such sides keep their authored elbow (R3 found 99 deg/key on PKM reloads).
        rel = Rot.from_quat(sd['rel_hand']); ax = np.asarray(sd['axis_l'], float)
        p0 = rr.unwrap([rr.twist((k['L'].inv() * k['H'] * rel.inv()).as_quat(), ax) for k in keys])
        p1 = rr.unwrap([rr.twist(((k['L'] * Rot.from_rotvec(ax * math.radians(b))).inv() * k['H'] * rel.inv()).as_quat(), ax)
                        for k, b in zip(keys, beta1)])                     # from the rotations: whole turns don't count
        step0 = np.abs(np.diff(p0)).max() if len(p0) > 1 else 0.0
        step1 = np.abs(np.diff(p1)).max() if len(p1) > 1 else 0.0
        if step1 > 1.5 * step0 + 1200.0 / rate: return plan(keys, ref, s, sd, rate, blend=False)
    keys1 = []
    for k, b in zip(keys, beta1):
        F = unit(k['W'] - k['E']); k1 = dict(k); k1['L'] = Rot.from_rotvec(F * math.radians(b)) * k['L']; keys1.append(k1)
    res = rr.plan_side(keys1, sd['rel_hand'], sd['axis_l'], rate, s)
    if blend and res is not None and any(w[2] == 'reroute' for w in res['windows']):
        # R3c: moving the elbow roll into the forearm must not itself push the hand past 180 about the forearm
        # (pistol inspects: hand fixed on the forearm, elbow turning to 175; the split then crossed 180 and the
        # re-route turned the forearm the other way round). Only keep it if the authored clip crosses anyway.
        res0 = rr.plan_side(keys, sd['rel_hand'], sd['axis_l'], rate, s)
        if res0 is None or not any(w[2] == 'reroute' for w in res0['windows']): return plan(keys, ref, s, sd, rate, blend=False)
    n = len(keys)
    if res is None:
        p = rr.unwrap([rr.twist((k['L'].inv() * k['H'] * Rot.from_quat(sd['rel_hand']).inv()).as_quat(), sd['axis_l']) for k in keys1])
        # keep the twist on the branch nearest 0 (no excursion beyond the range here by construction)
        p -= 360 * round(float(np.mean(p)) / 360)
        res = dict(alpha=np.zeros(n), beta=np.zeros(n), gamma=np.zeros(n), p2=p, windows=[])
    return dict(alpha=res['alpha'], beta=beta1 + res['beta'], gamma=res['gamma'], p_final=res['p2'], windows=res['windows'],
                elbow_keys=int((np.abs(beta1) > .5).sum()), changed=bool((np.abs(beta1) > .5).any() or res['windows']))


def rotations(k, alpha, beta, gamma, p_final, sd, shares=(1.0, 0.5)):
    """Component rotations for upperarm, lowerarm, hand, twist_01, twist_02."""
    A = unit(k['E'] - k['S']); F = unit(k['W'] - k['E']); ax = np.asarray(sd['axis_l'], float)
    U2 = Rot.from_rotvec(A * math.radians(alpha)) * k['U']
    L2 = Rot.from_rotvec(F * math.radians(beta)) * k['L']
    H2 = Rot.from_rotvec(F * math.radians(-gamma)) * k['H']
    T1 = L2 * Rot.from_rotvec(ax * math.radians(shares[0] * p_final)) * Rot.from_quat(sd['rel_t1'])
    T2 = L2 * Rot.from_rotvec(ax * math.radians(shares[1] * p_final)) * Rot.from_quat(sd['rel_t2'])
    return U2, L2, H2, T1, T2
