"""Collect existing saved-asset and requested review evidence. Launches no apps."""
from pathlib import Path
import hashlib
import json
import sys

base = Path(__file__).parent
project = base.parents[2]
run = Path(sys.argv[1])
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
install = read(base / 'install_receipt.json')
assets = read(base / 'assets-after.json')
native = read(base.parent / 'Wrist34/native_wrist_thirty_seven_final/receipt.json')['cases']
wire = read(run / 'receipt.json')
host = read(run / 'host.json')
client = read(run / 'client.json')
inventory = read(run / 'visual_capture_inventory.json')
guard = {}
for package, row in assets.items():
    file = project / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    guard[package] = hashlib.sha256(file.read_bytes()).hexdigest() == row['after']
assert all(guard.values()) and install['complete']
assert len(native) == 48 and all(row['passed'] for row in native)
assert wire['passed'] and host['passed'] and client['passed']
assert wire.get('clock') == 'real delta; 15 FPS cap; no fixed timestep'
assert all(not peer['owner_missing'] and not peer['remote_missing'] for peer in inventory.values())
assert all(len(peer['cases']) == 12 for peer in inventory.values())
for peer in inventory.values():
    assert len(peer['remote_action_segments']) == 12
    for group in peer['remote_action_segments']:
        assert sum(action in (2, 3) for action in group['actions']) == 1
        assert group['actions'][-1] == 0
result = dict(
    revision='Wrist37', saved=True, user_feel_acceptance='pending',
    network_visual_status='reviewed with real clock',
    scope='M249 belt box; six foregrip options through five existing profiles',
    changed_assets=[p for p, row in assets.items() if not row['unchanged']],
    unchanged_tracked_assets=sum(row['unchanged'] for row in assets.values()),
    approved_mesh_sha256=assets['/Game/Weapons/M249/SK_M249_V7']['after'],
    joint_rotation_only=read(base / 'scope_receipt.json')['joint_rotation_only'],
    native=dict(cases=len(native), passed=sum(row['passed'] for row in native),
                max_return_boundary_cm=max(row['return_boundary_cm'] for row in native)),
    wire=dict(receipt=wire, independent_owner_scenarios=24,
              result_rows=len(host['cases']) + len(client['cases']),
              max_owner_return_boundary_cm=max(row['return_boundary_cm'] for row in host['cases'] + client['cases'])),
    visual_capture=inventory,
    review=dict(
        evidence='Final UE viewport frames, runtime-skinned geometry closeups, owner and remote frame sequences',
        left='No recurrence of the reported severe wrist corkscrew in reviewed idle, support and regrip views.',
        right='Two-sided pickup, lift and lay closeups retain cartridge pinch and clear the receiver lugs.',
        transitions='Reviewed idle/ADS/return and sequential regrip/contact windows.',
        limits='Local listen-host plus one client with 80 ms lag and 2 percent loss each, real delta. Remote full-body frames establish pose synchronization, not sub-millimeter finger contact. Neutral closeups use diagnostic lighting; production mesh/materials are unchanged.'),
    asset_guard=guard)
(base / 'delivery.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(saved=True, native=result['native'], wire=wire,
                     owner_frames=sum(p['owner_frames'] for p in inventory.values()),
                     remote_frames=sum(p['remote_frames'] for p in inventory.values()),
                     changed_assets=len(result['changed_assets']), unchanged=result['unchanged_tracked_assets']), indent=2))
