"""Tie reviewed native poses to saved profiles and both real outfit routes."""
from pathlib import Path
import json,hashlib,gzip,numpy as np
O=Path(__file__).resolve().parent;P=O.parents[2]
candidate=json.loads((O/'native-candidate.json').read_text())
profiles=json.loads((O/'install_receipt.json').read_text())
glove=json.loads((O/'glove-install-receipt.json').read_text())
def digest(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
report={'complete':False,'assets_saved':profiles['complete'] and glove['complete'],'outfits':{},'protected':{},
        'interactive_game_tested':False,'V9_modified':False,'review_method':'real Gunplay graph; offline skin/morph reconstruction and neutral-material views'}
for mode in ['saved','saved-glove']:
    data=json.loads((O/('native-'+mode+'.json')).read_text())
    assert data['real_gunplay_graph'] and not data['candidate_transient']
    rows=[]
    for actual,expected in zip(data['families'],candidate['families']):
        family=actual['family'];assert family==expected['family'] and actual['names']==expected['names']
        assert len(actual['frames'])==len(expected['frames'])==110
        bone_error=max(float(np.max(abs(np.array(a['bones'])-np.array(b['bones'])))) for a,b in zip(actual['frames'],expected['frames']))
        morph_error=max(max(abs(a['morphs'].get(n,0)-w) for n,w in b['morphs'].items()) for a,b in zip(actual['frames'],expected['frames']))
        target=profiles['assets'][family]['path']
        assert all(r['profile'].split('.')[0]==target for r in actual['frames'])
        assert bone_error<1e-5 and morph_error<1e-5
        if mode=='saved-glove':
            carrier=next(s for s in actual['visible_surfaces'] if s['mesh'].split('.')[0]==glove['path'])
            assert set(glove['morphs'])==set(carrier['morph_names']) and carrier['leader']
        rows.append({'family':family,'frames':110,'maximum_bone_component_difference':bone_error,'maximum_morph_weight_difference':morph_error,'saved_profile':target})
    report['outfits'][mode]=rows
for name,spec in json.loads((O/'protected-inputs.json').read_text()).items():
    report['protected'][name]=digest(spec['path'])==spec['sha256'];assert report['protected'][name]
sources=json.load(gzip.open(O.parent/'QuickMeleeSVDReferenceR2_20261019/Inputs/compressed.json.gz','rt'))['clips']
for name,spec in sources.items():
    report['protected']['source_'+name]=digest(spec['path'])==spec['sha256'];assert report['protected']['source_'+name]
for spec in profiles['assets'].values():assert digest(spec['path'])==spec['sha256'] and spec['other_actions_identical']
assert digest(glove['path'])==glove['sha256'] and glove['base_position_error_cm']==0
surface=json.loads((O/'native-candidate-surface-check.json').read_text())['summary']
assert surface['maximum_bare_hand_folds']==surface['maximum_glove_hand_folds']==0
assert json.loads((O/'root-frustum-candidate.json').read_text())['passed']
assert json.loads((O/'stock-arm-candidate.json').read_text())['maximum_onscreen_penetrating_vertices']==0
report['surface_review']=surface;report['reviewed_candidate_pose_identical_to_saved']=True
report['complete']=True
(O/'final-receipt.json').write_text(json.dumps(report,indent=2))
print('SVCH_R3_SAVED_VERIFIED',sum(len(r)*110 for r in report['outfits'].values()),'native frames',flush=True)
