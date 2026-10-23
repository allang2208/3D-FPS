"""Switch only sling presentation to the saved gravity/contact revision."""
import hashlib,json,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/SimpleSlingBag20261022';R=BASE/'GravityFitR3'
plan=json.loads((R/'manifest.json').read_text());saved=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed') or saved['revision']!=plan['revision']:raise RuntimeError('Finish saving the gravity-fit assets')
for row in plan['variants']:
    if saved['variants'][row['profile']]['sha256']!=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest():
        raise RuntimeError('Unsaved sling fit '+row['profile'])
path=P/'Content/ColdSteelData/player_body.json';before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
outfit=cfg['outfits']['ue_simple_sling_bag'];bare=plan['variants'][0];owned=[]
updates={'world_mesh':bare['asset'],'world_mesh_by_shirt':{r['shirt']:r['asset'] for r in plan['variants'] if r['shirt']},
    'hanging_pack':bare['hanging_pack'],'hanging_pack_by_shirt':{r['shirt']:r['hanging_pack'] for r in plan['variants'] if r['shirt']}}
for key,value in updates.items():outfit[key]=value;owned.append(('outfits','ue_simple_sling_bag',key))
rigid=outfit['rigid_pack'];rigid['location']=bare['rigid_location'];rigid['rotation_quat']=plan['rotation_quat']
rigid['location_by_shirt']={r['shirt']:r['rigid_location'] for r in plan['variants'] if r['shirt']}
owned.extend(('outfits','ue_simple_sling_bag','rigid_pack',key) for key in ['location','rotation_quat','location_by_shirt'])
# The old response values remain available for the diagnostic legacy branch;
# normal gameplay selects hanging_pack and does not apply its rear-only guard.
receipt=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'](path,before,cfg,owned_paths=owned,producer=__file__)
record=dict(revision=plan['revision'],status='saved_and_integrated_awaiting_user_gameplay',
    config_receipt=receipt,retained_pouch=plan['retained_pouch'],variants=6,
    physics='presentation-only gravity/contact rigid proxy; two taut-length strap constraints; per-garment moving torso hulls',
    strap='fixed shoulder/chest; smooth free spans and shared sewn-end transform; current and previous deformation plus rotated normals',
    runtime_tested=False,user_accepted=False,inventory_changed=False,player_saves_changed=False)
(R/'published.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
design_path=BASE/'design.json';design=json.loads(design_path.read_text(encoding='utf-8'))
if design.get('motion_diagnostic'):design['legacy_inertia_diagnostic']=design['motion_diagnostic']
design.update(status=record['status'],motion=record['physics'],gravity_revision=plan['revision'],runtime_tested=False,user_accepted=False,
              gravity_publication=str(R/'published.json'),motion_diagnostic=None)
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2),encoding='utf-8')
print('SLING_GRAVITY_R3_PUBLISHED',receipt['status'],flush=True)
