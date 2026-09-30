"""How much forearm pronation the anatomical convention needs on the current reloads,
and how much an elbow swivel could remove (search on the shoulder-wrist circle)."""
import sys
import numpy as np
sys.path[:0] = [str(__import__('pathlib').Path(__file__).parents[1]), str(__import__('pathlib').Path(__file__).parent)]
import diag_lib as D
import rehinge as RH

BI = D.BI
for label, f in (('201 base reload', 'Tracks/base_b53_tracks.json.gz'), ('201 base empty', 'Tracks/base_empty_b53_tracks.json.gz'),
                 ('PKM reload_empty', 'Diagnostics/pkm_reload_empty_asbase.json.gz'), ('PKM reload', 'Diagnostics/pkm_reload_asbase.json.gz')):
    tr = D.load_tracks(D.HERE / f)
    W = D.worlds(tr, np.arange(0, len(tr['hand_l']), 3))
    _, info = RH.solve_clip(W, sigma_frames=1)
    b = info['bend'] > 35
    tau, phi = info['tau_deg'], info['phi_deg']
    # idle (first frame) pronation for reference
    print('%-17s bent frames %3d/%3d | helper roll off hinge now: %4.0f..%4.0f | anatomical pronation needed: %4.0f..%4.0f (idle %4.0f)' % (
        label, b.sum(), len(b), phi[b].min(), phi[b].max(), tau[b].min(), tau[b].max(), tau[0]))
    # per phase
    t = np.arange(len(W)) * 3 / 120
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6.6)):
        m = (t >= lo) & (t < hi) & b
        if m.any():
            print('     %.0f-%.0fs  bend %3.0f..%3.0f  roll-off %4.0f..%4.0f  pronation %4.0f..%4.0f' % (
                lo, hi, info['bend'][m].min(), info['bend'][m].max(), phi[m].min(), phi[m].max(), tau[m].min(), tau[m].max()))
