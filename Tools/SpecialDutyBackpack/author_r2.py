"""Produce the orientation repair for both current native body variants."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/SpecialDutyBackpack'))
import author as a
R=a.R
source=R/'BodyInputs'
inputs=a.read(source/'manifest.json')
canonical=a.read(source/inputs['rigs']['Jason']['body'])
male=canonical['reference']['spine_04']
male_axes=Rotation.from_quat(male[3:7]).as_matrix()
only=sys.argv[sys.argv.index('--rig')+1] if '--rig' in sys.argv else None
previous=a.read(R/'manifest.json') if only else {}
rows=[r for r in previous.get('variants',[]) if r['rig']!=only]
motions={k:v for k,v in previous.get('backpack_motion_by_rig',{}).items() if k!=only}
for rig,recipe in inputs['rigs'].items():
    if only and rig!=only:continue
    body=a.read(source/recipe['body'])
    target=body['reference']['spine_04']
    axes=Rotation.from_quat(target[3:7]).as_matrix()
    rotation=male_axes@axes.T
    translation=np.asarray(target[:3])-np.asarray(male[:3])@rotation
    normalized=source/'Normalized'/rig
    normalized.mkdir(parents=True,exist_ok=True)
    def normalize(data):
        out=copy.deepcopy(data)
        out['positions']=((np.asarray(data['positions'])-translation)@rotation.T).tolist()
        return out
    a.write(normalized/'body.json',normalize(body))
    for key,shirt in recipe['shirts'].items():
        data=normalize(a.read(source/shirt['base']))
        points=np.vstack([np.asarray(a.read(source/f)['points']).reshape(-1,3) for f in shirt['surfaces']])
        points=(points-translation)@rotation.T
        data['extra_fit_points']=points[(points[:,2]>84)&(points[:,2]<110)].tolist()
        a.write(normalized/(key+'.json'),data)
    pants=np.vstack([np.asarray(a.read(source/r['file'])['points']).reshape(-1,3) for r in recipe['waist_routes']])
    a.WAIST_POINTS=(pants-translation)@rotation.T
    a.RIG=rig
    a.I=normalized
    a.NATIVE_ROTATION=rotation
    a.NATIVE_TRANSLATION=translation
    a.TEMPLATE=recipe['template']
    shoulder=(np.asarray(body['reference']['clavicle_l'][:3])-translation)@rotation.T
    a.SHOULDER_SHIFT=float(shoulder[2]-canonical['reference']['clavicle_l'][2])
    a.BAG_CENTRE=np.asarray(a.CALIBRATION['body_center_cm'],float)+[0.,0.,a.SHOULDER_SHIFT]
    # Include the lower back and the actual rear panel, not just an upper-back
    # slope that lets a folded waist loop hold the entire shell away.
    a.BAG_ROTATION=np.eye(3)
    a.prepare_bag()
    from fit_mount import calibrate
    tilt=calibrate(a,normalize(body))
    a.BAG_ROTATION=Rotation.from_euler('x',tilt,degrees=True).as_matrix().T
    a.prepare_bag()
    a.PROFILES={key:(shirt,name.replace('Jason',rig).replace('Backpack','SpecialDutyBackpack'),margin)
                for key,(shirt,name,margin) in a.base.PROFILES.items()}
    covered={value[0] for value in a.PROFILES.values()}
    for shirt in recipe['shirts']:
        if shirt not in covered:
            profile=shirt.removeprefix('ue_')
            suffix=''.join(word.title() for word in profile.split('_'))
            a.PROFILES[profile]=(shirt,'SK_'+rig+'_SpecialDutyBackpack_'+suffix,.4)
    rig_rows=[a.build(profile) for profile in a.PROFILES]
    rows.extend(rig_rows)
    lo=np.min([r['bounds_min'] for r in rig_rows],axis=0)
    hi=np.max([r['bounds_max'] for r in rig_rows],axis=0)
    # The support pivot is recalibrated with the new worn body placement.
    centre=np.asarray(rig_rows[0]['rigid_location'])
    pivot=centre+np.array([0.,3.,12.])@a.BAG_ROTATION@rotation
    motions[rig]=dict(frequency_hz=3.0,damping=1.05,max_angle_degrees=1.2,max_bounce_cm=.15,
                      response_scale=1.5,max_displacement_cm=1.3,pivot=pivot.tolist(),
                      bounds_min=lo.tolist(),bounds_max=hi.tolist())
    a.write(R/'author_progress.json',{'variants':rows,'rigs_completed':list(motions)})
a.write(R/'manifest.json',dict(revision=a.REVISION,variants=rows,backpack_motion_by_rig=motions,
        original_source_preserved=True,decimation_applied=False,
        geometry='canonical shared Nanite body and fitted native harnesses for every current shirt route',
        fit_inputs=str(source/'manifest.json'),
        coverage={rig:{'shirts':len(r['shirts']),'pants_routes':len(r['waist_routes'])} for rig,r in inputs['rigs'].items()}))
print('SPECIAL_DUTY_R2_AUTHORED',len(rows),flush=True)
