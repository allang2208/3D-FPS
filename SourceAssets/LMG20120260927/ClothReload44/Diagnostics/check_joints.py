"""Per-family joint check for the authored ClothReload44 tracks (left arm)."""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

BI, REST = D.BI, D.REST
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
unit = lambda v: v / np.linalg.norm(v)
P = lambda n: REST[BI[n]][:3, 3]


def basis(a, b):
    a = unit(a); b = unit(b - a * (b @ a)); return np.column_stack((a, b, np.cross(a, b)))


def swing(a, b):
    a = unit(a); b = unit(b); q = np.r_[np.cross(a, b), 1 + np.clip(a @ b, -1, 1)]
    return R.from_quat(unit(q)).as_matrix()


U0, F0 = P('lowerarm_l') - P('upperarm_l'), P('hand_l') - P('lowerarm_l')
width = P('index_metacarpal_l') - P('pinky_metacarpal_l')
bind = basis(F0, width)
out = {}
for fam in ('base', 'vertical', 'canted', 'prism', 'angled'):
    tr = D.load_tracks(D.HERE / 'Tracks' / (fam + '_tracks.json.gz'))
    W = D.worlds(tr)
    dev = bend = 0.0
    for k in range(0, len(W), 2):
        w_ = W[k]
        s, e, h = (w_[BI[n]][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
        Dh = rot(w_[BI['hand_l']]) @ rot(REST[BI['hand_l']]).T
        fs = basis(h - e, Dh @ width) @ bind.T
        us = swing(fs @ U0, e - s) @ fs
        for n, sk in (('lowerarm_l', fs), ('lowerarm_twist_02_l', fs), ('lowerarm_twist_01_l', fs),
                      ('upperarm_twist_01_l', us), ('upperarm_twist_02_l', us)):
            dev = max(dev, np.degrees(R.from_matrix(rot(w_[BI[n]]) @ rot(REST[BI[n]]).T @ sk.T).magnitude()))
        bend = max(bend, np.degrees(np.arccos(np.clip(unit(Dh @ F0) @ unit(h - e), -1, 1))))
    E = W[:, BI['lowerarm_l'], :3, 3]
    H = W[:, BI['hand_l'], :3, 3]
    je = np.linalg.norm(np.diff(E, axis=0), axis=1).max() * 2
    jh = np.linalg.norm(np.diff(H, axis=0), axis=1).max() * 2
    q = np.array([R.from_matrix(rot(W[k, BI['lowerarm_l']])).as_quat() for k in range(len(W))])
    dq = np.abs(np.einsum('ij,ij->i', q[1:], q[:-1]))
    jr = np.degrees(2 * np.arccos(np.clip(dq, -1, 1))).max()
    eye = min(np.linalg.norm(W[k, BI[n], :3, 3] - D.camera(D.framing_alpha(k / 120))[0])
              for k in range(0, len(W), 3) for n in ('lowerarm_l', 'hand_l', 'lowerarm_twist_02_l'))
    out[fam] = dict(coherent_dev_deg=round(dev, 3), wrist_bend_max=round(bend, 1), elbow_jump_cm_per_60=round(je, 2),
                    hand_jump_cm_per_60=round(jh, 2), forearm_rot_step_deg_per_120=round(jr, 2),
                    bone_len_err_cm=round(D.bone_length_error(W), 5), min_eye_to_elbow_or_hand_cm=round(float(eye), 1))
    print(fam, out[fam], flush=True)
(D.HERE / 'Diagnostics' / 'joint_check_v2.json').write_text(json.dumps(out, indent=2))
