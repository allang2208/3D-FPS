import json,math
from pathlib import Path
O=Path(__file__).parent
ue=json.loads((O/'ue_readback.json').read_text());detail=json.loads((O/'ue_finger_tracks.json').read_text());bones=json.loads((O/'bone_tracks.json').read_text())
samples=[dict(asset=k,**r) for k,a in ue['assets'].items() for r in a.get('samples',[])]
scale=sum(detail['coordinate_probe']['hand_l']['world']['scale'])/3
for row in detail['samples']:
 for b in row['finger_tracks']:b['physical_local_translation_delta_mm']=b['local_translation_delta_api_units']*scale*10
out={'scope':'Read-only authoring geometry/animation and saved UE data; no PIE, no production writes',
 'assets_read':len(ue['assets']),'ue_sampled_poses':len(samples),'max_compression_position_error':max(samples,key=lambda r:r['max_position_error_mm']),
 'max_compression_rotation_error':max(samples,key=lambda r:r['max_rotation_error_deg']),
 'coordinate_calibration':{'ue_WORLD':'centimetres; compared muzzle/root displacement with authored metre landmark','ue_LOCAL':'before inherited root scale; multiply by inherited scale before cm-to-mm conversion','inherited_scale':scale},
 'ue_finger_track_findings':[dict(clip=r['clip'],frame=r['frame'],worst=r['finger_tracks'][0]) for r in detail['samples']],
 'geometry_samples_per_family':{f:len(json.loads((O/f'geometry_{f}.json').read_text())) for f in bones},
 'sprint_exit_wrist_degrees':{f:next(r['idle_return']['hand_l']['rotation_deg'] for r in rows if r['clip']=='sprint_exit' and r['frame']==48) for f,rows in bones.items()},
 'images':[p.name for p in sorted(O.glob('0*.jpg'))]}
(O/'summary.json').write_text(json.dumps(out,indent=2))
print('SVD_AUDIT_SUMMARY',out['assets_read'],out['ue_sampled_poses'])
print('COMPRESSION_MM',out['max_compression_position_error']['max_position_error_mm'])
for r in out['ue_finger_track_findings']:
 if (r['clip'],r['frame']) in [('reload',128),('reload_empty',128),('equip',100),('reload_empty',350)]:print(r)
