"""Assemble requested native front/side captures and record the scoped review."""
import json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/IdleCrossedR7';V=R/'Review';E=V/'EngineFinal';O=V/'Delivery';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assets=read(E/'assets.json');contact=read(V/'contact_review.json');saved=read(R/'saved_asset.json')
finish=read(R/'robe_finish_saved.json')
if not finish['completed']:raise RuntimeError('Cloth finish has not been saved')
if assets['idle_asset']!=saved['asset']:raise RuntimeError('Unexpected runtime animation')
for target in ('FPSGAMEEditor','FPSGAME'):
 if read(R/'Build'/(target+'-build.json'))['exit_code']!=0:raise RuntimeError('Build incomplete')
report=dict(status='saved_integrated_and_reviewed',animation=saved['asset'],source_blend=str(R/'Nun_Crossed_Idle_R7.blend'),
 editor_build='success',game_build='success',pose='Original hands overlapping in front, with lowered elbows, reduced forward reach and forearm-aligned palms',
 duration_seconds=12,production_actor_offscreen_capture=assets['production_actor_assembly'],saved_compressed_pose_samples=len(contact['samples']),
 hand_hand_crossings=sum(sum(x['hand_pair_crossings'].values()) for x in contact['samples']),
 exposed_hand_cloth_crossings=sum(v['hand_edge_cloth_crossings']+v['cloth_edge_hand_crossings'] for x in contact['samples'] for v in x['sides'].values()),
 cuff_torso_crossings=sum(v['cuff_edge_torso_crossings']+v['torso_edge_cuff_crossings'] for x in contact['samples'] for v in x['sides'].values()),
 cuff_pair_crossings=sum(v['cuff_other_sleeve_crossings'] for x in contact['samples'] for v in x['sides'].values()),
 interactive_gameplay_tested=False,screenshots=[str(E/'front.png'),str(E/'profile_left.png'),str(E/'hand_left.png'),str(E/'hand_left_side.png')])
report.update(robe_finish=finish,dialogue_integrated=True,conversation_facing='Per-local-client body yaw; no replicated turn target',
 village_plans={'wall':'unlock plan only; ruined and repaired designs exist','blacksmith':'unlock plan only; ruined and repaired designs exist'},
 holy_light='Nun trainer only for new learning; existing earned progress retained; character Lv15',multiplayer_runtime_tested=False)
(R/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('NUN_CROSSED_R7_DELIVERED',report['hand_hand_crossings'],report['exposed_hand_cloth_crossings'])
