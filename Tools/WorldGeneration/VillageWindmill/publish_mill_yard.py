"""Publish the mill kit first and the village last, under the UE bridge batch lock."""
import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

try:
    import unreal as ue
except ImportError:
    ue=None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def replace(source,target,expected):
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        shutil.copyfile(source,temp)
        if digest(target)!=expected:
            raise RuntimeError('New revision on disk: '+str(target))
        os.replace(temp,target)
    finally:
        temp.unlink(missing_ok=True)


def publish(project,batch,run):
    content=(project/'Content').resolve()
    host=run/'Host/Content'
    report=json.loads((run/'level-saved.json').read_text(encoding='utf-8'))
    level=report['level']
    rel=Path(level.removeprefix('/Game/')+'.umap')
    source,target=host/rel,content/rel
    before=digest(Path(report['previous_package']))
    staged=digest(source)
    if not before or not staged or staged==before:
        raise RuntimeError('Missing staged village change or recovery copy')
    previous_file=run/'previous-yard.json'
    previous=json.loads(previous_file.read_text(encoding='utf-8')) if previous_file.exists() else {}
    current=digest(target)
    world=None
    if ue:
        if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve()!=project.resolve():
            raise RuntimeError('Bridge is attached to a different project')
        if level in {p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()}:
            raise RuntimeError('Village has unsaved editor changes')
        world=ue.find_object(None,level+'.'+rel.stem)
        if world and ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
            raise RuntimeError('Village in active play session; resume when released')
        if not world and ue.find_object(None,level):
            raise RuntimeError('Village package is still held by the editor')
    if current not in (before,staged):
        raise RuntimeError('Village changed since staging; restage using the newest map')
    copies=[]
    paths=[]
    for file in sorted((host/'WorldGeneration/TemperateHills/VillageWindmill/Yard').rglob('*')):
        if not file.is_file():
            continue
        suffix=file.relative_to(host)
        dest=content/suffix
        pkg='/Game/'+suffix.with_suffix('').as_posix()
        if file.suffix=='.uasset':
            paths.append(pkg)
        present=digest(dest)
        if present==digest(file):
            continue
        if present!=previous.get(suffix.as_posix()):
            raise RuntimeError('Different production asset: '+pkg)
        if ue and (ue.find_object(None,pkg) or ue.find_object(None,pkg+'.'+suffix.stem)):
            raise RuntimeError('Mill asset is already loaded: '+pkg)
        copies.append((file,dest,present))
    for file,dest,present in copies:
        if present:
            old=run/'Before'/'Assets'/dest.relative_to(content)
            old.parent.mkdir(parents=True,exist_ok=True)
            if not old.exists():
                shutil.copy2(dest,old)
        replace(file,dest,present)
    if ue:
        # The registered mount is /Game. Resolving the Content junction yields an
        # F: filename that the running D: project cannot convert to a package.
        registry=ue.AssetRegistryHelpers.get_asset_registry()
        registry.scan_paths_synchronous(['/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard'],True)
    if world and current!=staged:
        # Edit the held world in place without switching the user's open map.
        site=ue.find_object(None,report['site'])
        if not isinstance(site,ue.HillsWindmill) or 'VillageWindmill.Site' not in map(str,site.tags):
            raise RuntimeError('The held world has no matching mill site')
        tools=project/'Tools/WorldGeneration'
        sys.path[:0]=[str(tools/'VillageWindmill'),str(tools/'AbandonedVillage')]
        from mill_yard import install_mill_yard
        backup=run/'Before'/'Loaded'/target.name
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(target,backup)
        report.update(install_mill_yard(site),previous_package=str(backup))
        if digest(target)!=current or not ue.EditorLoadingAndSavingUtils.save_map(world,level):
            raise RuntimeError('Could not save the current village revision')
    elif current!=staged:
        replace(source,target,before)
        if ue:
            mounted=ue.Paths.convert_relative_path_to_full(ue.Paths.project_content_dir())
            registry.scan_modified_asset_files([(Path(mounted)/rel).as_posix()])
    report.update(map_sha256=digest(target),production_map=str(target),packages=paths)
    body=json.dumps(report,indent=2,ensure_ascii=False)
    (run/'published.json').write_text(body,encoding='utf-8')
    (batch/'published.json').write_text(body,encoding='utf-8')
    print('WINDMILL_YARD_PUBLISHED '+str(batch/'published.json'))
