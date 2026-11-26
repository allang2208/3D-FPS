"""Publish only this revision's male/female worn-mesh leaves."""
import json,runpy,hashlib,shutil,os,uuid
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1'
KEY='ue_modern_tactical_helmet'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved.json');before=read(R/'capture.json')
if not saved['completed']:raise RuntimeError('Save must finish before publication')
review=read(R/'static-clearance.json')
if not review.get('completed'):raise RuntimeError('Requested static LOD inspection is not complete')
stage=Path(saved['content_root']).resolve()
if stage!=(R/'StageHost/Content').resolve():raise RuntimeError('Unexpected asset stage')
installed=[]
for rig in ['Jason','Kaitlin']:
    asset=saved['meshes'][rig]['asset'];relative=Path(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
    source=stage/relative;target=P/'Content'/relative
    for ext in ['.uasset','.uexp','.ubulk']:
        src=source.with_suffix(ext);dst=target.with_suffix(ext)
        if not src.exists():
            if ext=='.uasset':raise RuntimeError('Staged asset missing: '+str(src))
            continue
        digest=hashlib.sha256(src.read_bytes()).hexdigest();dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            if hashlib.sha256(dst.read_bytes()).hexdigest()!=digest:raise RuntimeError('Conflicting new helmet asset: '+str(dst))
        else:
            temporary=dst.with_name(dst.name+'.hairfit-'+uuid.uuid4().hex+'.tmp');shutil.copy2(src,temporary)
            # A new revision never replaces an existing package.
            os.rename(temporary,dst)
        installed.append({'file':str(dst),'sha256':digest})
path=P/'Content/ColdSteelData/player_body.json';raw=path.read_bytes();cfg=json.loads(raw.decode('utf-8-sig'));owned=[]
for rig,fields in [('Jason',['head_equipment',KEY]),('Kaitlin',['body_variants','kaitlin','head_equipment',KEY])]:
    obj=cfg
    for key in fields:obj=obj[key]
    new=saved['meshes'][rig]['asset'];old=before['profiles'][rig]['helmet']['static_mesh']
    if obj['static_mesh'] not in (old,new):raise RuntimeError('Concurrent helmet mesh change: '+rig)
    if obj.get('covers_scalp_hair',False):raise RuntimeError('Whole-hair visibility policy changed: '+rig)
    if hashlib.sha256((R/'Authored'/f'helmet_{rig}_wear.json').read_bytes()).hexdigest()!=saved['meshes'][rig]['sha256']:raise RuntimeError('Unsaved author change: '+rig)
    obj['static_mesh']=new;owned.append(tuple(fields+['static_mesh']))
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit']
receipt=commit(path,raw,cfg,owned_paths=owned,producer=__file__)
(R/'published.json').write_text(json.dumps(dict(completed=True,config=receipt,meshes=saved['meshes'],installed=installed,native_hair_preserved=True,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('HELMET_HAIR_FIT_PUBLISHED')
