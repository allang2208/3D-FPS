"""Update delivery metadata after production authoring, never an acceptance test."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
c=json.loads((R/'Config/scene.json').read_text('utf8'))
m=json.loads((R/'Authored/manifest.json').read_text('utf8'))
parts=[p for s in c['rooms']+c['connectors'] for p in s.get('reused_parts',[])]
native=[p for s in c['rooms'] for p in s.get('scene_containers',[])]
auth=[p for s in c['rooms'] for p in s.get('authored_parts',[])]
counts=dict(new_fbx=len(m['objects']),authored_triangles=sum(o['triangles'] for o in m['objects']),
    ucx_hulls=sum(o['simple_collision_hulls'] for o in m['objects']),
    reused_source_types_used=len(set(p['source_asset_id'] for p in parts)),reused_mesh_instances=len(parts),
    reused_static_actors=sum(not p.get('container_id') for p in parts),native_containers=len(native),
    lights=sum(len(s['lights']) for s in c['rooms']+c['connectors']),
    shadowed_lights=sum(bool(l['cast_shadows']) for s in c['rooms']+c['connectors'] for l in s['lights']),
    authored_actor_instances=sum(not o.get('prototype') for o in m['objects'])+len(auth))
sha=lambda p:hashlib.sha256((R/p).read_bytes()).hexdigest()
p=R/'Receipts/delivery-status.json';d=json.loads(p.read_text('utf8'))
d.update(revision=c['revision'],counts=counts,source_manifest_sha256=sha('Authored/manifest.json'),
    scene_json_sha256=sha('Config/scene.json'),materials_sha256=sha('Config/materials.json'))
correction='Extended both connector floors/slabs beneath full ±1.86m wall footprint, without moving jamb ownership faces.'
if correction not in d['static_corrections']:d['static_corrections'].append(correction)
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
p=R/'Docs/refine-v2-static-snapshot.json';s=json.loads(p.read_text('utf8'))
s.update(production_hashes_pending_final_export=False,counts=counts,manifest_sha256=d['source_manifest_sha256'],scene_sha256=d['scene_json_sha256'])
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_SOURCE_RECEIPTS_FINALIZED',json.dumps(counts))
