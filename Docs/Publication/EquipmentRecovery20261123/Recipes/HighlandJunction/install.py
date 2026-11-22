from pathlib import Path
from datetime import datetime
import json,hashlib,os,tempfile
try:
    import unreal as ue
except ImportError:
    ue=None
W=Path('F:/FPSGAME-Recovery-Work-20261120/HighlandClaymoreJunction20261121')
project=Path('D:/FPS3D/FPSGAME')
job=json.loads((W/'job.json').read_bytes())
saved=json.loads((W/'saved.json').read_bytes())
if set(job['targets'])!=set(saved):raise RuntimeError('Incomplete staged batch')
def sha(b):return hashlib.sha256(b).hexdigest()
def replace(p,b):
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:
        f.write(b)
        tmp=Path(f.name)
    try:os.replace(tmp,p)
    finally:tmp.unlink(missing_ok=True)
prepared={}
for k in job['targets']:
    rel=Path(k[6:]+'.uasset')
    f=project/'Content'/rel
    src=(W/'Host/Content'/rel).read_bytes();before=(W/'Before'/rel).read_bytes()
    if sha(before)!=job['before'][k] or src[:4]!=bytes.fromhex('c1832a9e'):raise ValueError(k)
    if f.read_bytes() not in (before,src):raise RuntimeError('Target changed since production snapshot: '+k)
    prepared[k]=(f,src,before)
loaded=[]
changed=[]
def reload_targets(ks):
    packages=[p for k in ks for p in [ue.find_package(k)] if p]
    if packages:
        ok,msg=ue.EditorLoadingAndSavingUtils.reload_packages(packages,ue.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
        if not ok or str(msg):raise RuntimeError('Reload: '+str(msg))
if ue:
    if Path(ue.Paths.project_dir()).resolve()!=project.resolve():raise RuntimeError('Wrong editor project')
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world() is not None:raise RuntimeError('ACTIVE_PIE: preserving running game')
    dirty={p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(prepared):raise RuntimeError('UNSAVED_HIGH­LAND_PACKAGE '+str(dirty.intersection(prepared)))
    loaded=[k for k in prepared if ue.find_package(k)]
    if loaded:ue.EditorLoadingAndSavingUtils.fully_load_packages([ue.find_package(k) for k in loaded])
try:
    for k,(f,src,before) in prepared.items():
        current=f.read_bytes()
        if current==src:continue
        if current!=before:raise RuntimeError('Concurrent target change '+k)
        replace(f,src);changed.append(k)
    if ue:
        reload_targets([k for k in changed if k in loaded])
        paths=[str(prepared[k][0]) for k in changed if k not in loaded]
        if paths:ue.AssetRegistryHelpers.get_asset_registry().scan_modified_asset_files(paths)
except Exception:
    for k in reversed(changed):
        f,src,before=prepared[k]
        if f.read_bytes()==src:replace(f,before)
    if ue and loaded:reload_targets([k for k in changed if k in loaded])
    raise
summary=dict(when=datetime.now().isoformat(),commit='b22184fe',assets=[dict(package=k,old_sha256=sha(before),new_sha256=sha(src),bytes=len(src),source=saved[k]) for k,(f,src,before) in prepared.items()],backup=str(W/'Before'),applied_via='existing editor bridge' if ue else 'offline installation under project mutex',runtime_tested=False)
(W/'installed.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('HIGHLAND_JUNCTION_PUBLISHED '+str(len(prepared)))
