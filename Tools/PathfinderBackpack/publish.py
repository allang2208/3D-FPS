"""Publish the saved orientation repair, scoped to this item and both bodies."""
import hashlib
import json
import runpy
import shutil
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024'
KEY='ue_pathfinder_backpack'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'manifest.json')
saved=read(R/'saved_assets.json')
if not saved.get('completed') or saved['revision']!=plan['revision']:
    raise RuntimeError('Save this revision before publication')
for row in plan['variants']:
    rec=saved['variants'][row['profile']]
    if not rec['saved'] or rec['sha256']!=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest():
        raise RuntimeError('Unsaved harness '+row['profile'])
for key in ['Display','Worn']:
    folder=R/'Authored'/key
    digest=hashlib.sha256(b''.join((folder/(n+'.bin')).read_bytes() for n in ['positions','normals','uv','triangles','materials'])).hexdigest()
    if not saved.get(key,{}).get('saved') or saved[key]['sha256']!=digest:
        raise RuntimeError('Unsaved static '+key)
writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))
config=P/'Content/ColdSteelData/player_body.json'
before=config.read_bytes()
candidate=json.loads(before.decode('utf-8-sig'))
owned=[]
for rig in ['Jason','Kaitlin']:
    rows=[r for r in plan['variants'] if r['rig']==rig]
    bare=next(r for r in rows if not r['shirt'])
    root=('outfits',KEY) if rig=='Jason' else ('body_variants','kaitlin','outfits',KEY)
    outfit=candidate['outfits'][KEY] if rig=='Jason' else candidate['body_variants']['kaitlin']['outfits'][KEY]
    values={'world_static_mesh':saved['Display']['asset'],
            'world_mesh':saved['variants'][bare['profile']]['asset'],
            'world_mesh_by_shirt':{r['shirt']:saved['variants'][r['profile']]['asset'] for r in rows if r['shirt']},
            'rigid_pack':{'mesh':saved['Worn']['asset'],'location':bare['rigid_location'],
                          'rotation_quat':bare['rigid_rotation_quat'],
                          'location_by_shirt':{r['shirt']:r['rigid_location'] for r in rows if r['shirt']}},
            'backpack_motion':plan['backpack_motion_by_rig'][rig]}
    for key,value in values.items():
        outfit[key]=value
        owned.append(root+(key,))
body_receipt=writer['commit'](config,before,candidate,owned_paths=owned,producer=__file__)
# The live equipment icon reads world_static_mesh. Both the canonical fallback
# and old item snapshots still read Icons/<definition>.png, so update that too.
icon=P/'Content/ColdSteelData/Icons/ue_pathfinder_backpack.png'
backup=R/'Before/ue_pathfinder_backpack.png'
if icon.exists() and not backup.exists():shutil.copy2(icon,backup)
# Preserve the current catalog PNG; finish via Tools/BackpackIcons/run.ps1.
# source_icon.png is a Blender authoring reference, not the inventory camera.
result={'item':KEY,'revision':plan['revision'],'status':'saved_and_integrated_awaiting_user_gameplay',
        'variants':len(plan['variants']),'rigs':['Jason','Kaitlin'],'coverage':plan['coverage'],
        'player_body_receipt':body_receipt,'catalog_fields_unchanged':True,'icon':str(icon),
        'icon_export_pending':True,'icon_export_entry':'Tools/BackpackIcons/run.ps1 -Definitions ue_pathfinder_backpack',
        'saved_assets':str(R/'saved_assets.json'),'source_triangles':193071,
        'runtime_tested':False,'network_tested':False,'player_saves_modified':False,
        'native_code_changed':False,'git_commit':None,'git_push':None}
(R/'published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PATHFINDER_R2_PUBLISHED',len(plan['variants']),flush=True)
