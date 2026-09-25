"""Build the natural-extension target: the shipping round-1 root, untouched,
with the two distal segments brought to the SVD's light 4/3 deg flexion.

The root is taken from the round-1 receipt (authoring.json) and cross-checked
against the round-1 blend that is shipping, so the web is not rotated at all -
only the thumb's own two distal joints straighten.
"""
import json
from pathlib import Path

O = Path(__file__).parent
receipt = json.loads((O / 'authoring.json').read_text())
fit = json.loads((O / 'thumb_fit.json').read_text())
web = json.loads((O / 'thumb_web_check.json').read_text())
C, D = 4.0, 3.0
out = {}
for gun in ('AKM', 'A762'):
    key = '%s/standard/base/reload' % gun
    root = receipt[key]['thumb_target']['thumb_01_l']
    if abs(root[2]) > 1e-9:
        raise SystemExit('%s round-1 root is not twist-free: %s' % (gun, root))
    cand = next(x for x in web[gun]['candidates'] if x['name'] == 'installed_flex43')
    shipped = next(x for x in web[gun]['candidates'] if x['name'] == 'installed_as_shipped')
    out[gun] = {'root_quat_wxyz': root, 'c_02': C, 'd_03': D,
                'root_source': 'authoring.json %s thumb_target.thumb_01_l (round-1, shipping)' % key,
                'shipping_root_wxyz': web[gun]['shipping_root_wxyz'],
                'root_swing_vs_shipping_deg': cand['root_swing_vs_shipping_deg'],
                'visible_len_mm': cand['visible_len_mm'],
                'visible_vs_rest_pct': cand['visible_vs_rest_pct'],
                'angle_to_mag_deg': cand['angle_to_mag_deg'],
                'rise_mm': cand['rise_mm'],
                'web_gap_mm': cand['web_gap_mm'],
                'web_skin_moved_vs_shipping_mm': cand['web_skin_moved_vs_shipping_mm'],
                'pad_min_mm': cand['pad_min_mm'],
                'shipping': {'visible_len_mm': shipped['visible_len_mm'],
                             'visible_vs_rest_pct': shipped['visible_vs_rest_pct'],
                             'angle_to_mag_deg': shipped['angle_to_mag_deg'],
                             'rise_mm': shipped['rise_mm'],
                             'c_02': shipped['c_02'], 'd_03': shipped['d_03']},
                'round1_fit_params': fit[gun]['params']}
    print('%s -> root %s (unchanged, twist-free), flexion %.0f/%.0f' % (gun, root, C, D), flush=True)
    print('   visible %.1f mm (%.1f%% of rest) at %.1f deg to the magazine, rise %+.1f, web gap %.2f mm (moved %.2f mm), pad %s'
          % (cand['visible_len_mm'], cand['visible_vs_rest_pct'], cand['angle_to_mag_deg'], cand['rise_mm'],
             cand['web_gap_mm'], cand['web_skin_moved_vs_shipping_mm'], cand['pad_min_mm']), flush=True)
    print('   was   %.1f mm (%.1f%%) at %.1f deg, rise %+.1f  with flexion %.1f/%.1f'
          % (shipped['visible_len_mm'], shipped['visible_vs_rest_pct'], shipped['angle_to_mag_deg'],
             shipped['rise_mm'], shipped['c_02'], shipped['d_03']), flush=True)
(O / 'thumb_target3.json').write_text(json.dumps(out, indent=1))
print('SELECT_V3_OK', flush=True)
