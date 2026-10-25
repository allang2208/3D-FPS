"""Publish the saved slender revision; preserve all capacity and other equipment tuning."""
import hashlib
import json
import os
import runpy
import tempfile
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/FarreachBackpack20261024';R=ROOT/'SlimFitR2_20261024'
KEY='ue_farreach_backpack'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'manifest.json');saved=read(R/'saved_assets.json')
if not saved.get('completed') or saved['revision']!=plan['revision']:
    raise RuntimeError('Save the current authored revision before publication')
for row in plan['variants']:
    if saved['variants'][row['profile']]['sha256']!=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest():
        raise RuntimeError('Harness source differs from saved asset '+row['profile'])
for kind in ['Display','Worn']:
    folder=R/'Authored'/kind
    digest=hashlib.sha256(b''.join((folder/(n+'.bin')).read_bytes() for n in ['positions','normals','uv','triangles','materials'])).hexdigest()
    if saved[kind]['sha256']!=digest:raise RuntimeError('Static source differs from saved asset '+kind)

writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))
baseline=read(R/'Before/player_body.json')
config=P/'Content/ColdSteelData/player_body.json';before=config.read_bytes();candidate=json.loads(before.decode('utf-8-sig'));owned=[]
for rig in ['Jason','Kaitlin']:
    rows=[row for row in plan['variants'] if row['rig']==rig];bare=next(row for row in rows if not row['shirt'])
    collection=candidate['outfits'] if rig=='Jason' else candidate['body_variants']['kaitlin']['outfits']
    old=baseline['outfits'][KEY] if rig=='Jason' else baseline['body_variants']['kaitlin']['outfits'][KEY]
    root=('outfits',KEY) if rig=='Jason' else ('body_variants','kaitlin','outfits',KEY)
    fields={'world_static_mesh':saved['Display']['asset'],'world_mesh':saved['variants'][bare['profile']]['asset'],
            'world_mesh_by_shirt':{row['shirt']:saved['variants'][row['profile']]['asset'] for row in rows if row['shirt']},
            'rigid_pack':{'mesh':saved['Worn']['asset'],'location':bare['rigid_location'],'rotation_quat':bare['rigid_rotation_quat'],
                          'location_by_shirt':{row['shirt']:row['rigid_location'] for row in rows if row['shirt']}},
            'backpack_motion':plan['backpack_motion_by_rig'][rig]}
    for field,value in fields.items():
        if collection[KEY].get(field)!=old.get(field) and collection[KEY].get(field)!=value:
            raise RuntimeError('Concurrent Farreach presentation edit: '+rig+'/'+field)
        collection[KEY][field]=value;owned.append(root+(field,))
body_receipt=writer['commit'](config,before,candidate,owned_paths=owned,producer=__file__)

catalog=P/'Content/ColdSteelData/items.json'
with writer['_lock'](P/'Saved/FarreachPublication/items.lock'):
    before=catalog.read_bytes();current=json.loads(before.decode('utf-8-sig'))
    old=read(R/'Before/items.json')[KEY]
    value=saved['Display']['asset']
    if current[KEY].get('world_mesh') not in (old.get('world_mesh'),value):
        raise RuntimeError('Concurrent Farreach pickup mesh edit')
    text=writer['_set'](before.decode('utf-8-sig'),(KEY,'world_mesh'),value)
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    with tempfile.NamedTemporaryFile(dir=catalog.parent,prefix='.farreach-slim-',suffix='.tmp',delete=False) as f:
        temp=Path(f.name);f.write(after);f.flush();os.fsync(f.fileno())
    try:
        if catalog.read_bytes()!=before:raise RuntimeError('Catalog changed during publication; retry from current data')
        os.replace(temp,catalog)
    finally:
        if temp.exists():temp.unlink()

result={'revision':plan['revision'],'status':'saved_and_integrated_awaiting_user_gameplay','item':KEY,
        'variants':len(plan['variants']),'coverage':plan['coverage'],'player_body_receipt':body_receipt,
        'catalog_updated_fields':['world_mesh'],'capacities_changed':False,'player_saves_modified':False,
        'geometry':read(R/'source_prepared.json'),'mounts':{rig:read(R/('mount_calibration_'+rig+'.json'))['selected'] for rig in ['Jason','Kaitlin']},
        'saved_assets':str(R/'saved_assets.json'),'icon_export_pending':True,
        'runtime_tested':False,'network_tested':False,'native_code_changed':False}
(R/'published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design=read(ROOT/'design.json');design.update(status=result['status'],production_revision=plan['revision'],
    implementation_receipt='SlimFitR2_20261024/published.json',source_dimensions_cm=result['geometry']['dimensions_cm'],
    proportions='52 cm wide, 70 cm tall; all source faces and UV retained; inverse-scale normals',
    model_created=True,imported_to_ue=True,user_accepted_model=False,runtime_tested=False,catalog_icon_exported=False)
(ROOT/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FARREACH_SLIM_PUBLISHED',len(plan['variants']),flush=True)
