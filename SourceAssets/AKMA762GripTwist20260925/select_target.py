"""Select the aimed-up thumb target per gun from the closed-form visible aim.

Rule: keep the round-1 root's roll (the correction is a minimal-arc swing, so no
twist is added), keep the two distal segments nearly straight at 4/3 deg, and
swing the visible thumb direction to 22 deg off the magazine's own long axis -
the smallest swing that still leaves the distal phalanx beside the magazine
rather than inside it.  Result: the visible thumb is 102-103 % of its rest length
(the chain is straightened, not curled) and rises ~56 mm.
"""
import json
from pathlib import Path

O = Path(__file__).parent
aim = json.loads((O / 'thumb_aim_vis2.json').read_text())
fit = json.loads((O / 'thumb_fit.json').read_text())
TILT, C, D, VARIANT = -22.0, 4.0, 3.0, 'from_round1'
out = {}
for gun, data in aim.items():
    rows = [x for x in data['candidates'] if x['variant'] == VARIANT and abs(x['tilt'] - TILT) < .01
            and x['c_02'] == C and x['d_03'] == D]
    if not rows:
        raise SystemExit('no candidate for %s' % gun)
    b = rows[0]
    near = [x for x in data['candidates'] if x['variant'] == VARIANT and x['c_02'] == C and x['d_03'] == D]
    out[gun] = {'source_path': data['path'], 'frame': data['frame'],
                'mag_axis_armature': data['mag_axis_armature'],
                'variant': VARIANT, 'tilt': b['tilt'], 'c_02': b['c_02'], 'd_03': b['d_03'],
                'root_quat_wxyz': b['root_quat_wxyz'],
                'vis_len_mm': b['vis_len_mm'], 'vis_vs_rest_pct': b['vis_vs_rest_pct'],
                'angle_to_mag_deg': b['angle_to_mag_deg'], 'rise_mm': b['rise_mm'],
                'along_mag_mm': b['along_mag_mm'], 'clear': b['clear'],
                'baselines': {'rest_vis_len_mm': data['rest_vis_len_mm'],
                              'round1_vis_len_mm': data['round1_vis_len_mm'],
                              'round1_angle_deg': data['round1_angle_deg'],
                              'round1_params': fit[gun]['params']},
                'neighbouring_tilts': [{'tilt': x['tilt'], 'angle_to_mag_deg': x['angle_to_mag_deg'],
                                        'rise_mm': x['rise_mm'], 'vis_vs_rest_pct': x['vis_vs_rest_pct'],
                                        'clear': x['clear'], 'root_quat_wxyz': x['root_quat_wxyz']}
                                       for x in near if abs(x['tilt'] - TILT) <= 4.0 and x['tilt'] != TILT]}
    print('%s -> %s tilt %.0f flex %.0f/%.0f  visible %.1f mm (%.1f%% of rest)  angle %.2f deg  rise %+.1f  pad %s'
          % (gun, VARIANT, b['tilt'], b['c_02'], b['d_03'], b['vis_len_mm'], b['vis_vs_rest_pct'],
             b['angle_to_mag_deg'], b['rise_mm'],
             {k: b['clear'][k]['min'] for k in ('thumb_01_l', 'thumb_02_l', 'thumb_03_l')}), flush=True)
    print('   quat %s   (round-1 visible %.1f mm at %.1f deg, rest %.1f mm)'
          % ([round(x, 6) for x in b['root_quat_wxyz']], data['round1_vis_len_mm'],
             data['round1_angle_deg'], data['rest_vis_len_mm']), flush=True)
(O / 'thumb_target2.json').write_text(json.dumps(out, indent=1))
print('SELECT_VIS_OK', flush=True)
