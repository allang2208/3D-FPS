"""Check actual pose selection, native joint stations and stock contact."""
from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_surfaces import *
O=HERE
mode=sys.argv[1] if len(sys.argv)>1 else 'candidate'
old=json.loads((O/'native-baseline.json').read_text())
new=json.loads((O/('native-'+mode+'.json')).read_text())
stock=np.array([-.006067879,-.216416583,.028199226,1.]);root=ids['WPN_root'];hand=ids['hand_r']
assert new['real_gunplay_graph'] and len(new['families'])==5
report={'mode':mode,'families':{},'passed':True}
for family,prior in zip(new['families'],old['families']):
    assert family['family']==prior['family']
    order=[family['names'].index(n) for n in names];oldorder=[prior['names'].index(n) for n in names]
    ps=[matrices(np.array(r['bones'])[order]) for r in family['frames']]
    bs=[matrices(np.array(r['bones'])[oldorder]) for r in prior['frames']]
    station=max(max(offsets(p).values()) for p in ps)
    contact=next(i for i,r in enumerate(family['frames']) if r['frame']==20)
    contact_error=float(np.linalg.norm((ps[contact][root]@stock-bs[contact][root]@stock)[:3]))
    morph=max(max(r['morphs'].values(),default=0) for r in family['frames'])
    weights_error=0.
    for row,p in zip(family['frames'],ps):
        expected=driver.weights(matrix_pose(p))
        weights_error=max(weights_error,max((abs(row['morphs'].get(n,0)-w) for n,w in expected.items()),default=0))
    row={'native_joint_offset_error_cm':station,'stock_contact_error_cm':contact_error,'maximum_runtime_morph_weight':morph,
         'runtime_vs_source_driver_weight_error':weights_error,'visible_surfaces':family['visible_surfaces'],
         'alpha_start':family['frames'][1]['action_alpha'],'alpha_contact':family['frames'][contact]['action_alpha'],
         'alpha_end':family['frames'][-1]['action_alpha'],'profile':family['frames'][contact]['profile']}
    row['passed']=station<.01 and contact_error<.02 and morph>.1 and weights_error<.005 and row['alpha_contact']>.99
    report['passed'] &= row['passed'];report['families'][family['family']]=row
(O/('native-'+mode+'-contract.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
if not report['passed']:raise SystemExit(1)
