"""Focused readback of the existing native Gunplay capture, without game launch."""
from pathlib import Path
import sys,json,numpy as np
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'QuickMeleeHandR3_20261019'))
import check_surfaces as s
sys.path.insert(0,str(O.parent/'QuickMeleeSVDChainR4_20261020'))
from action_framing import camera_for_frame
mode=sys.argv[1] if len(sys.argv)>1 else 'saved-glove'
capture=json.loads((O/f'native-{mode}.json').read_text())
assert capture['real_gunplay_graph'] and len(capture['families'])==5
fields=np.load(O.parent/'QuickMeleeHandR3_20261019/glove-correctives.npz')
s.blue.extra={k:fields[k] for k in fields.files}
s.O=O
sequences=[]
T=s.bare.T
edges=np.sort(np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1)
edges,count=np.unique(edges,axis=0,return_counts=True)
vi=s.bare.first[np.unique(edges[count==1])]
bn=np.array([s.names[j] for j in s.bare.weights.argmax(1)])
vi=np.array([j for j in vi if bn[j].startswith(('upperarm','clavicle')) and bn[j].endswith('_r')])
root_rows=[];weight_error=0.;rows=[]
for family in capture['families']:
    order=[family['names'].index(n) for n in s.names]
    camera=s.matrices([family['view_to_camera']])[0]
    tx=np.tan(np.radians(family['camera_horizontal_fov']/2));ty=tx/family['camera_aspect']
    # The supplied user screenshot is ultrawide. At the same vertical FOV,
    # inspect the wider 2.65:1 projection as well as the captured 16:9 one.
    tx=max(tx,ty*2.65)
    samples=[]
    for row in family['frames']:
        fi=row['frame'];p=s.matrices(np.array(row['bones'])[order]);morphs=row['morphs']
        samples.append((fi,p,morphs,row['action_alpha']))
        expected=s.driver.weights(s.matrix_pose(p))
        weight_error=max(weight_error,max((abs(morphs.get(n,0)-v) for n,v in expected.items()),default=0))
        view=camera_for_frame(camera,fi)
        v=s.bare.evaluate(p,morphs)[vi];v=v@view[:3,:3].T+view[:3,3]
        on=(v[:,0]>1)&(abs(v[:,1])<v[:,0]*tx)&(abs(v[:,2])<v[:,0]*ty)
        if on.any():root_rows.append({'family':family['family'],'frame':fi,'vertices':int(on.sum())})
    sequences.append((family['family'],samples))
    rows.append({'family':family['family'],'frames':len(samples),'visible_surfaces':family['visible_surfaces']})
s.collect('native-'+mode,sequences)
surface=json.loads((O/f'native-{mode}-surface-check.json').read_text())['summary']
result={'mode':mode,'families':rows,'surface':surface,'root_cut_in_stationary_action_camera':root_rows,
        'runtime_driver_weight_error':weight_error,
        'camera_evidence':'Native graph bones and runtime weights; stationary UpdateViewmodel camera reconstructed from existing source',
        'root_projection_aspects':[16/9,2.65],
        'interactive_game_tested':False}
result['bone_driver_camera_checks_passed']=surface['maximum_joint_offset_error_cm']<.01 and not root_rows and weight_error<.005
# Face-normal disagreement also occurs on the unchanged V9 elbow/knuckle
# creases. Retain those counts for visual inspection; they are not a complete
# intersection test and do not turn this receipt into visual acceptance.
result['visual_accepted']=False
result['surface_counts_are_normal_disagreement_heuristic']=True
(O/f'review-{mode}.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('families','root_cut_in_stationary_action_camera')}),flush=True)
if not result['bone_driver_camera_checks_passed']:raise SystemExit(1)
