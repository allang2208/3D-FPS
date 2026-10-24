"""Publish only this single-pistol source family after all clips are saved."""
import json,runpy,hashlib
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/GitHubSinglePistol20261022'
r=json.loads((OUT/'retarget-receipt.json').read_text(encoding='utf8'))
end=json.loads((OUT/'EndBind_retarget-receipt.json').read_text(encoding='utf8'))
r['clips'].update(end['clips'])
crouch=json.loads((OUT/'CrouchInitBind_retarget-receipt.json').read_text(encoding='utf8'))
r['clips'].update(crouch['clips'])
roles={'Idle':'RevolverAimIdle','Walk':'RevolverAimWalk','Fire':'RevolverAimShoot',
    'Crouch.Idle':'RevolverCrouchAimIdle','Crouch.Walk':'RevolverCrouchAimWalk',
    'Reload.Init':'RevolverReloadInit','Reload.Loop':'RevolverReloadLoop','Reload.End':'RevolverReloadEnd',
    'Crouch.Reload.Init':'RevolverCrouchAimReloadInit','Crouch.Reload.Loop':'RevolverCrouchAimReloadLoop','Crouch.Reload.End':'RevolverCrouchAimReloadEnd'}
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
if cfg['body_mesh']!=r['target']:raise RuntimeError('Target body changed during authoring')
keys={};files={}
for role,name in roles.items():
    asset=r['clips'][name];file=ROOT/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
    if not file.is_file():raise RuntimeError('Missing saved clip '+asset)
    key='SinglePistol.Source.'+role;keys[key]=asset;cfg['clips'][key]=asset
    files[str(file.relative_to(ROOT))]=hashlib.sha256(file.read_bytes()).hexdigest()
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
write=commit(path,before,cfg,owned_paths=[('clips',key) for key in keys],producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(clips=keys,sha256=files,config_write=write,assets_saved=True,
    runtime_tested=False,git_commit=None,git_push=None),indent=2),encoding='utf8')
print('GITHUB_SINGLE_PISTOL_PUBLISHED',len(keys))
