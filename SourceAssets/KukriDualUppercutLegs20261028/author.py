"""Transfer the installed single uppercut support to the existing dual take.

Only the pelvis/lower subtree is copied. The dual spine boundary compensates
the pelvis orientation change, retaining both weapon arm chains and fingers.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SINGLE=ROOT/'SourceAssets/KukriSingleUppercutLegs20261027'
spec=importlib.util.spec_from_file_location('native_lower',ROOT/'SourceAssets/KukriUppercutSwordLower20261027/author.py')
lower=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lower)


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    inputs=json.loads((OUT/'inputs.json').read_text())
    saved=json.loads((SINGLE/'assets-saved.json').read_text())
    if not saved.get('complete'):raise RuntimeError('Single uppercut source has not been saved')
    report=dict(version='Dual uppercut supported legs V1',bodies={},first_person_changed=False,
        single_changed=False,cpp_changed=False,runtime_tested=False,rendered=False)
    for label,body_data in lower.base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        captured=inputs[label]
        original=captured['previous']
        raw=(SINGLE/(label+'-actions.json')).read_bytes()
        source=json.loads(raw)
        receipt=saved['bodies'][label]
        source_asset=receipt['clips']['Kukri.FullBody.Uppercut']
        if hashlib.sha256(raw).hexdigest()!=receipt['source_sha256']:
            raise RuntimeError('Saved single uppercut source differs from author data: '+label)
        if active['clips']['Kukri.FullBody.Uppercut']!=source_asset or active['clips']['Kukri.FullBody.Dual.Uppercut']!=original['asset']:
            raise RuntimeError('Uppercut route changed during preparation: '+label)
        if active['body_mesh']!=body_data['mesh'] or source['names']!=captured['names'] or source['names']!=body_data['names']:
            raise RuntimeError('Native body source mismatch: '+label)
        body=lower.c.Body(body_data)
        donor=source['clips']['Uppercut']
        frames=np.asarray(original['frames'],dtype=float)
        donor_frames=np.asarray(donor['frames'],dtype=float)
        if donor['rate_num']/donor['rate_den']!=original['rate'] or frames.shape!=donor_frames.shape:
            raise RuntimeError('Uppercut timelines differ: '+label)
        for marker,key in [('Contact','contact'),('Release','release')]:
            if abs(original['markers'][marker]-donor[key]*original['duration'])>1e-5:
                raise RuntimeError('Uppercut contact clock differs: '+label)
        _,original_q=body.world(frames)
        source_endpoints=frames[[0,-1]].copy()
        ids=lower.lower_bones(body)
        frames[:,ids]=donor_frames[:,ids]
        spine=body.ix['spine_01']
        body.set_world_rotations(frames,{spine:R.from_quat(original_q[:,spine])})
        # Shared stance boundaries differ only by UE's saved float rounding;
        # retain the captured dual endpoints so handoff uses its own stance.
        frames[0]=source_endpoints[0];frames[-1]=source_endpoints[-1]
        for k in range(1,len(frames)):
            frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
        duration=(len(frames)-1)/original['rate']
        clip=dict(rate_num=int(original['rate']),rate_den=1,frames=frames.tolist(),
            contact=original['markers']['Contact']/duration,release=original['markers']['Release']/duration,
            source=source_asset,
            adaptation='Single uppercut supported legs copied on the same contact clock; original dual shoulder, wrist and finger chains retained with spine-boundary compensation')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=source['mesh'],names=source['names'],parents=source['parents'],clips={'Dual.Uppercut':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=source['mesh'],previous_roles={'Dual.Uppercut':original['asset']},
            source_single=source_asset,source_single_sha256=receipt['source_sha256'],frames=len(frames),
            transferred_lower_bones=[body.names[i] for i in ids],upper_boundary='spine_01 component rotation preserved')
        print('DUAL_UPPERCUT_LEGS_AUTHORED',label,len(frames),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
