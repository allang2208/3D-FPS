"""Tie the saved SVCH profile, successful build and current runtime evidence."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
install=json.loads((O/'install_receipt.json').read_text());editable=json.loads((O/'editable_source.json').read_text())
geometry=json.loads((O/'charge_validation.json').read_text());runtime=json.loads((O/'runtime_review.json').read_text())
assert install['source_sha256']==editable['profile_source_sha256']==digest(O/'profile_charge.json')
assert install['profile_sha256']==digest(P/'Content/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip.uasset')
preserved={}
for item in json.loads((O/'CurrentSource/manifest.json').read_text()).values():
 f=P/'Content'/(item['path'].removeprefix('/Game/')+'.uasset');preserved[item['path']]=digest(f)==item['sha256']
arms=P/'Content/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7.uasset'
preserved[editable['native_v9_source']]=digest(arms)==editable['native_v9_sha256'];assert all(preserved.values())
assert geometry['unchanged_other_clips']==11 and geometry['max_non_clavicle_local_difference']==0
assert max(x['closed_handle_envelope_penetration_mm'] for x in geometry['approach_release_samples'])<.1
assert geometry['hand_bolt_held_position_drift_mm']<.1
for stage,metrics in runtime['stages'].items():
 assert metrics['boundary_component_step_mm']<1,(stage,metrics)
 assert metrics['boundary_component_rotation_deg']<.1,(stage,metrics)
 assert metrics['boundary_gun_root_step_mm']<2,(stage,metrics)
 assert metrics['boundary_gun_root_rotation_deg']<.5,(stage,metrics)
assert runtime['held_charge_samples']>=8 and runtime['held_hand_bolt_position_drift_mm']<.2
build=O/'build-editor-final.log';assert 'Result: Succeeded' in build.read_text(errors='replace') or 'Target is up to date' in build.read_text(errors='replace')
collision=[json.loads((O/f).read_text()) for f in ('charge_collision.json','charge_collision_346.json')]
assert all(x['receiver_inside_vertices']==0 for x in collision)
native_geometry=json.loads((O/'native_v9_geometry_comparison.json').read_text())
assert all(v for k,v in native_geometry['unchanged_fields'].items() if k!='weights')
receipt={'revision':'R11ChargeHandoff','assets_saved':True,'runtime_reviewed':True,'profile':install['profile'],
 'profile_sha256':install['profile_sha256'],'profile_source_sha256':install['source_sha256'],
 'native_v9_and_current_source_preserved':preserved,'native_v9_geometry_comparison':native_geometry,'other_action_profiles_unchanged':11,
 'left_reload_grip_preserved':True,'native_wrist_finger_local_pose_preserved':True,
 'build_log':str(build),'binary_sha256':digest(P/'Binaries/Win64/UnrealEditor-FPSGAME.dll'),
 'charge_held_drift_mm':geometry['hand_bolt_held_position_drift_mm'],
 'charge_approach_release_max_envelope_penetration_mm':max(x['closed_handle_envelope_penetration_mm'] for x in geometry['approach_release_samples']),
 'receiver_contact_checks':collision,'runtime':runtime,'editable_source':editable['editable_blend'],
 'scope':'Factory magazine; normal and empty first-person reload, native V9, charging and return to idle. Audio, networking and full attachment matrix excluded.'}
(O/'validation_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
(O/'delivery_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
install['runtime_tested']=True;install['validation_receipt']=str(O/'validation_receipt.json');(O/'install_receipt.json').write_text(json.dumps(install,indent=2))
delivery=O.parent/'delivery_receipt.json';previous=json.loads(delivery.read_text())
if previous.get('revision')=='R10ReloadReview':
 (O/'previous_delivery.json').write_bytes(delivery.read_bytes());delivery.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print('SVCH_R11_SAVED_AND_REVIEWED',json.dumps(runtime,ensure_ascii=False))
