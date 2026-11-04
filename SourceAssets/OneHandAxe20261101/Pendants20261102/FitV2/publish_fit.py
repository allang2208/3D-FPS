"""Publish only the four new saved packages and merge three hatchet recipes."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3];HOST=P.parent/'ImportProject'
receipt=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not receipt['complete']:raise RuntimeError('Fitted meshes have not finished saving')
report=json.loads((P/'SavedMeshCheck/geometry_report.json').read_text('utf-8'))
if len(report['pairs'])!=12 or any(r['intersecting_face_pairs'] or r['penetrating_vertices_gt_0_025mm'] or not r['hole_midplane_edge_crossings'] for r in report['pairs']):
    raise RuntimeError('Saved mesh through-hole inspection did not pass')
files=[]
for asset in receipt['saved_assets']:
    rel=Path(asset.split('.')[0].removeprefix('/Game/')).with_suffix('.uasset')
    target=ROOT/'Content'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as dest:dest.write((HOST/'Content'/rel).read_bytes())
    files.append(str(target))
path=ROOT/'Content/ColdSteelData/tactical-hatchet-modules.json'
original=path.read_bytes();catalog=json.loads(original)
for entry in receipt['parts']:
    spec=catalog['slots']['lanyard'][entry['id']]
    spec.update({k:entry[k] for k in ['mesh','materials','material_slot_names','location_cm']})
    spec['mount_revision']='HatchetCordFitV2'
    spec['collision_capsules_cm'][0]=[-1.35,0,-.55,1.75,0,-.55,.95]
if path.read_bytes()!=original:raise RuntimeError('Concurrent hatchet catalog edit preserved')
(P/'Before').mkdir(exist_ok=True)
(P/'Before/tactical-hatchet-modules.json').write_bytes(original)
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out={'complete':True,'files':files,'parts':receipt['parts'],'static_mesh_pairs_checked':12,
     'geometry_report':'SavedMeshCheck/geometry_report.json','runtime_animation_tested':False,
     'mount_revision':'HatchetCordFitV2'}
(P/'registration_receipt.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('HATCHET_FITTED_PENDANTS_PUBLISHED assets='+str(len(files)))
