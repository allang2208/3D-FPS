"""Retire only the approved bedroom sample map after formal apartment publication."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,shutil,hashlib,gc
R=Path(__file__).resolve().parent;PROJECT=R.parents[3]
PILOT='/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024'
FORMAL='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    installed=json.loads((R/'installed.json').read_text('utf8'))
    if installed['stage']!='formal_apartment_saved':raise RuntimeError('Save the formal apartment first')
    archive=PROJECT/'trash/cyberpunk-bedroom-pilot-retired-20261024'
    content=(PROJECT/'Content').resolve();archive=archive.resolve()
    if not archive.is_relative_to((PROJECT/'trash').resolve()):raise RuntimeError('Archive path outside task trash')
    subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if subsystem and subsystem.get_game_world():raise RuntimeError('Preserve the current PIE session')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map work')
    current=subsystem.get_editor_world() if subsystem else None
    if not current or current.get_path_name().split('.')[0]!=FORMAL:
        u.EditorLoadingAndSavingUtils.load_map(FORMAL)
    gc.collect();u.SystemLibrary.collect_garbage()
    refs=E.find_package_referencers_for_asset(PILOT,False) if E.does_asset_exist(PILOT) else []
    if refs:raise RuntimeError('Sample map still has package consumers: '+str(refs))
    rows=[];packages=[PILOT,PILOT+'_BuiltData']
    for package in packages:
        relative=Path('Content')/(package.removeprefix('/Game/')+('.umap' if package==PILOT else '.uasset'))
        path=(PROJECT/relative).resolve()
        if not path.is_relative_to(content):raise RuntimeError('Retirement path outside Content')
        files=[p for p in [path,path.with_suffix('.uexp'),path.with_suffix('.ubulk')] if p.exists()]
        for file in files:
            dest=archive/file.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
            sha=digest(file)
            if dest.exists() and digest(dest)!=sha:raise RuntimeError('Different earlier archive at '+str(dest))
            if not dest.exists():shutil.copy2(file,dest)
            rows.append(dict(original=str(file),archive=str(dest),size=file.stat().st_size,sha256=sha,reason='Bedroom V3 integrated into the existing apartment; sample map retired',replacement=FORMAL))
        if E.does_asset_exist(package) and not E.delete_asset(package):raise RuntimeError('Could not retire '+package)
        for file in files:
            if file.exists():raise RuntimeError('Retired package file remains '+str(file))
    for kind in ('__ExternalActors__','__ExternalObjects__'):
        directory=(content/kind/'GameMaps/Design/L_CyberpunkBedroom_Pilot20261024').resolve()
        if directory.exists() and any(p.is_file() for p in directory.rglob('*')):
            raise RuntimeError('Sample external packages need explicit retirement: '+str(directory))
    report=dict(stage='sample_map_retired',formal_map=FORMAL,retired_map=PILOT,retired_at=datetime.now().astimezone().isoformat(),files=rows,game_run=False)
    (R/'retired.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    archive.mkdir(parents=True,exist_ok=True);(archive/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('BEDROOM_SAMPLE_RETIRED',len(rows))
if __name__=='__main__':main()
