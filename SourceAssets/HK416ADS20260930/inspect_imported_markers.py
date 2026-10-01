"""Inspect only the two corrected sight markers in the saved HK416 actions."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930'
auth=json.loads((S/'authoring.json').read_text());root='/Game/Weapons/HK416/Reworked20260930'
mesh=u.load_asset(root+'/SK_HK416_Manny')
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
options.evaluation_type=u.AnimDataEvalType.COMPRESSED
rows=[]
for key in auth['clips']:
    family,kind=key.split('/');path=root+'/Animations/'+family+'/A_HK416_'+family+'_'+kind
    anim=u.load_asset(path)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,0.,options)
    transforms={name:u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD) for name in ('WPN_root','WPN_RearSight','WPN_FrontSight')}
    weapon=transforms['WPN_root']
    rear=weapon.inverse_transform_location(transforms['WPN_RearSight'].translation)
    front=weapon.inverse_transform_location(transforms['WPN_FrontSight'].translation)
    expected_rear=4*.03739+auth['source_to_weapon_root'][2][3]
    expected_front=4*.03627359+auth['source_to_weapon_root'][2][3]
    errors=[abs(rear.z-expected_rear),abs(front.z-expected_front)]
    rows.append({'clip':key,'rear_root_local':list(rear.to_tuple()),'front_root_local':list(front.to_tuple()),'marker_height_error_m':errors,'corrected_heights':max(errors)<.00005})
report={'scope':'compressed imported sight marker heights at clip start; no gameplay or animation regression','clips':rows,'all_corrected_heights':all(row['corrected_heights'] for row in rows)}
(O/'imported_marker_inspection.json').write_text(json.dumps(report,indent=2))
u.log('HK416_IMPORTED_SIGHT_MARKERS '+json.dumps({'clips':len(rows),'all_corrected_heights':report['all_corrected_heights']}))
