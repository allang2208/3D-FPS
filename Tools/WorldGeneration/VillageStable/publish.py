"""Publish the private stable packages followed by the village revision from which they were staged."""
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT=Path(os.environ['STABLE_PROJECT'])
RUN=Path(os.environ['STABLE_RUN'])
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'VillageWindmill'))
from publish_mill_yard import digest,replace,ue


def publish():
    content=(PROJECT/'Content').resolve()
    host=RUN/'Host/Content'
    report=json.loads((RUN/'level-saved.json').read_text(encoding='utf-8'))
    map_only=report.get('scope') in ('perimeter','riding')
    previous={} if map_only else json.loads((RUN/'previous-kit.json').read_text(encoding='utf-8-sig'))
    level=report['level']
    rel=Path(level.removeprefix('/Game/')+'.umap')
    before=digest(Path(report['previous_package']))
    staged=digest(host/rel)
    target=content/rel
    current=digest(target)
    if not staged or not before or staged==before or current not in (before,staged):
        raise RuntimeError('Village revision changed; run the Level phase again with the latest map.')
    world=None
    if ue:
        if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve()!=PROJECT.resolve():
            raise RuntimeError('Active editor belongs to another project.')
        if level in {p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()}:
            raise RuntimeError('Village has unsaved editor changes.')
        world=ue.find_object(None,level+'.'+rel.stem)
        if world and ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
            raise RuntimeError('Village is held by active play.')
        if not world and ue.find_object(None,level):
            raise RuntimeError('Village package is still held.')
    packages=[]
    copies=[]
    kit='WorldGeneration/TemperateHills/VillageStable'
    ground_only=report.get('scope')=='ground_detail'
    horse_only=report.get('scope')=='horses'
    scope_dir=host/kit
    if ground_only:
        scope_dir/='GroundDetailR4'
    elif horse_only:
        scope_dir/='Horses'
    kit_files=[] if map_only else sorted(scope_dir.rglob('*'))
    for file in kit_files:
        if not file.is_file():
            continue
        suffix=file.relative_to(host)
        dest=content/suffix
        pkg='/Game/'+suffix.with_suffix('').as_posix()
        new=digest(file)
        old=digest(dest)
        packages.append(dict(file=suffix.as_posix(),sha256=new))
        if new==old:
            continue
        if old!=previous.get(suffix.as_posix()) or (ue and ue.find_object(None,pkg)):
            raise RuntimeError('Stable asset has a different or loaded revision: '+pkg)
        copies.append((file,dest,old))
    for file,dest,old in copies:
        if old:
            backup=RUN/'Before/Kit'/dest.relative_to(content)
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists():
                shutil.copy2(dest,backup)
        replace(file,dest,old)
    if ue:
        registry=ue.AssetRegistryHelpers.get_asset_registry()
        registry.scan_paths_synchronous(['/Game/'+kit],True)
    if world and current!=staged:
        sys.path.insert(0,str(HERE))
        from install_stable import install_stable
        from stable_perimeter import install_stable_perimeter
        from stable_ground_detail import install_ground_detail
        from stable_horses import install_horses
        active=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        if active!=world:
            raise RuntimeError('Village is open outside the active editing world.')
        install={'ground_detail':install_ground_detail,'perimeter':install_stable_perimeter,
                 'horses':install_horses,'riding':lambda actors:install_horses(actors,upgrade_placed=True)}.get(report.get('scope'),install_stable)
        report.update(install(ue.get_editor_subsystem(ue.EditorActorSubsystem)))
        if digest(target)!=current or not ue.EditorLoadingAndSavingUtils.save_map(world,level):
            raise RuntimeError('Could not save the held village revision.')
    elif current!=staged:
        replace(host/rel,target,before)
        if ue:
            registry.scan_modified_asset_files([(PROJECT/'Content'/rel).as_posix()])
    report.update(packages=packages,production_map=str(target),previous_sha256=before,map_sha256=digest(target))
    output=json.dumps(report,indent=2,ensure_ascii=False)
    for directory in (RUN,RUN.parent):
        (directory/'published.json').write_text(output,encoding='utf-8')
    print('STABLE_PUBLISHED',len(packages),report['map_sha256'])


if __name__=='__main__':
    publish()
