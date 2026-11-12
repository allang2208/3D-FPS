"""Close the requested review only after the real-clock peers finish."""
from pathlib import Path
import sys,json,hashlib
here=Path(__file__).resolve().parent;project=here.parents[2];run=Path(sys.argv[1])
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assets=read(here/'assets-after.json');guard={}
for package,row in assets.items():
    path=project/'Content'/(package.removeprefix('/Game/')+'.uasset')
    guard[package]=hashlib.sha256(path.read_bytes()).hexdigest()==row['after']
assert all(guard.values()) and read(here/'install_receipt.json')['complete']
native=read(here.parent/'Wrist34/native_wrist_thirty_eight_final/receipt.json')['cases']
assert len(native)==48 and all(c['passed'] for c in native)
wire=read(run/'receipt.json');inventory=read(run/'visual_capture_inventory.json')
assert wire['passed'] and wire['clock']=='real delta; 15 FPS cap; no fixed timestep'
for peer in inventory.values():
    assert len(peer['cases'])==12 and not peer['owner_missing'] and not peer['remote_missing']
    assert len(peer['remote_action_segments'])==12
    for group in peer['remote_action_segments']:
        assert sum(x in (2,3) for x in group['actions'])==1 and group['actions'][-1]==0
scope=read(here/'scope_receipt.json');measure=read(here/'contact_measurements_final.json')
assert all(r['native_hand_vertices_inside_box_hull']==0 for rows in measure.values() for r in rows)
contact=[]
for name,rows in measure.items():
    shift=.9 if 'empty' in name else 0
    hold=[r for r in rows if 4.52-shift<=r['source']<=5.10-shift]
    contact.append(dict(case=name,samples=len(hold),max_tip_vertex_gap_cm=max(v for r in hold for v in r['tip_vertex_gaps_cm'].values())))
assert max(c['max_tip_vertex_gap_cm'] for c in contact)<.15
result=dict(revision='Wrist38',saved=True,user_feel_acceptance='pending',asset_guard=guard,
    changed_assets=[p for p,r in assets.items() if not r['unchanged']],
    unchanged_tracked_assets=sum(r['unchanged'] for r in assets.values()),
    joint_rotation_only=scope['joint_rotation_only'],left_arm_unchanged=True,fingers_unchanged=True,
    changed_clips=len(scope['changed_clips']),unchanged_clips=scope['unchanged_clips'],
    finding='W37 intermediate reach passed through the box and receiver; two-sided dense capture exposed it.',
    fix='Lateral withdrawal and rise before cartridge pinch, solved using right shoulder/elbow/wrist rotations only.',
    native=dict(cases=48,passed=48,max_return_boundary_cm=max(c['return_boundary_cm'] for c in native)),
    geometry=dict(cases=36,frames=840,left_skin_max_change_cm=max(read(here/'left_skin_preserved.json').values()),
                  capture=str(here.parent/'Wrist34/geometry_wrist_thirty_eight_final'),contact=contact),
    wire=dict(receipt=wire,independent_owner_scenarios=24,inventory=inventory),
    visual_review='Dense native palm/back views and actual owner/remote sequences reviewed; see README and review artifacts.',
    limits='Local listen host plus one client, 80 ms lag and 2 percent loss each; contact closeups use neutral diagnostic lighting on actual exported runtime skin. User feel acceptance remains pending.')
(here/'delivery.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(saved=True,native_passed=48,wire_passed=wire['passed'],
    owner_frames=sum(p['owner_frames'] for p in inventory.values()),remote_frames=sum(p['remote_frames'] for p in inventory.values()),
    max_hold_tip_vertex_gap_cm=max(c['max_tip_vertex_gap_cm'] for c in contact)),indent=2))
