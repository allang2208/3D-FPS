"""Publish the photographed package through the live editor without changing other open levels."""
from pathlib import Path
import unreal as u,shutil,hashlib,json,os
r=Path(r'D:/FPS3D/FPSGAME/SourceAssets/FreightCartBay20261113')
p=r.parents[1];target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
expected='05f9fcab6487b74b101c765dfb59e7c2f3e1f28a5e97cc1146ff54714aece3df'
def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def publish():
    if Path(u.Paths.project_dir()).resolve()!=p.resolve():raise RuntimeError('Wrong project')
    if not (r/'done-14.json').exists():raise RuntimeError('Private save missing')
    dst=p/rel;src=r/'RenderHost'/rel
    if digest(dst)!=expected:raise RuntimeError('Target map was changed since the photo')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    world=editor.get_editor_world();opened=u.find_object(None,target+'.'+target.rsplit('/',1)[1])
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if any(pkg.get_name().lower()==target.lower() for pkg in dirty):raise RuntimeError('The target level has unsaved edits')
    if opened and (not world or opened!=world or editor.get_game_world()):raise RuntimeError('Target is in use in another world')
    if opened and dirty:raise RuntimeError('Loaded session has unsaved maps')
    backup=r/'prior-map.umap'
    if not backup.exists():shutil.copy2(dst,backup)
    if digest(backup)!=expected:raise RuntimeError('Backup mismatch')
    if opened:
        if not u.EditorLoadingAndSavingUtils.new_blank_map(False):raise RuntimeError('Could not release the saved target before refresh')
    try:
        tmp=dst.with_suffix('.cartbay.tmp');shutil.copyfile(src,tmp)
        if digest(dst)!=expected or digest(tmp)!=digest(src):raise RuntimeError('Map package changed')
        os.replace(tmp,dst)
    finally:
        if opened:
            new=u.EditorLoadingAndSavingUtils.load_map(target)
            if not new:raise RuntimeError('Live level refresh failed')
    if digest(dst)!=digest(src):raise RuntimeError('Published package mismatch')
    (r/'published.json').write_text(json.dumps(dict(map=target,original=expected,saved=digest(dst),backup=str(backup),view='REF_02_CartSurface',refreshed_loaded_target=bool(opened)),indent=2),'utf8')
publish()
