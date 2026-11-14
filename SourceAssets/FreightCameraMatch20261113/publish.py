"""Commit the photographed map without switching the artist's current level."""
from pathlib import Path
import hashlib,json,shutil,os
import unreal as u
ROOT=Path(r'D:/FPS3D/FPSGAME/SourceAssets/FreightCameraMatch20261113')
PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
REL=Path('Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap')
BASE_HASH='b6cc5d43dd6796d1c9b842ffb2fc198b4ff049222775c900b35737cc4f33979b'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def publish():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Unexpected project')
    destination=PROJECT/REL;source=ROOT/'RenderHost'/REL
    if not (ROOT/'after-capture.json').is_file() or not (ROOT/'private-save.json').is_file():raise RuntimeError('Photographed private map has not been saved')
    release=json.loads((ROOT/'private-save.json').read_text('utf8'))
    if digest(source)!=release['hash'] or digest(destination)!=BASE_HASH:raise RuntimeError('Map version changed; preserve both versions')
    dirty=[p.get_path_name().lower() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())]
    if any(p==TARGET.lower() or ('/'+TARGET[6:].lower()+'/') in p for p in dirty):raise RuntimeError('Target contains unsaved changes')
    backup=ROOT/'before-original.umap'
    if not backup.exists():shutil.copy2(destination,backup)
    if digest(backup)!=BASE_HASH:raise RuntimeError('Existing backup differs')
    exists=u.find_object(None,TARGET+'.'+TARGET.rsplit('/',1)[-1])
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if exists:
        if not ed or ed.get_editor_world()!=exists or ed.get_game_world():raise RuntimeError('Target is loaded elsewhere; preserve the loaded package')
        # Apply the same photographed changes to the live level. Keep its camera and editor state intact.
        import runpy
        for entry in release['recipe']:
            runpy.run_path(str(ROOT/entry['script']))['run'](exists,entry)
        if not u.EditorLoadingAndSavingUtils.save_map(exists,TARGET):raise RuntimeError('Level save failed')
        method='live_level'
    else:
        tmp=destination.with_suffix('.freight-match.tmp')
        shutil.copyfile(source,tmp)
        if digest(tmp)!=release['hash'] or digest(destination)!=BASE_HASH:raise RuntimeError('Changed during copy')
        os.replace(tmp,destination);method='identical_photographed_package'
    (ROOT/'published.json').write_text(json.dumps(dict(map=TARGET,method=method,original=BASE_HASH,saved=digest(destination),backup=str(backup)),indent=2),'utf8')
publish()
