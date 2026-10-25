"""Resave the selected native heads' hard animation dependencies, with backups."""
import gc,hashlib,json,os,shutil
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
def main():
    body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    configs=[body,body['body_variants']['kaitlin']]
    roots=[c['heads'][c['default_head']]['mesh'].split('.')[0] for c in configs]
    registry=u.AssetRegistryHelpers.get_asset_registry()
    options=u.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=False,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
    visited=set();pending=list(roots);selected={}
    while pending:
        package=pending.pop()
        if package in visited or not package.startswith('/Game/'):continue
        visited.add(package)
        for data in registry.get_assets_by_package_name(package,True):
            kind=str(data.asset_class_path.asset_name)
            if kind in ['AnimSequence','Skeleton','PoseAsset']:selected[str(data.package_name)+'.'+str(data.asset_name)]=kind
        pending.extend(str(x) for x in registry.get_dependencies(package,options) if str(x) not in visited)
    result={'roots':roots,'dependency_packages':len(visited),'selected':selected,'backups':{},'saved':[],'pose_tracks_edited':False}
    for path in selected:
        package=path.split('.')[0].removeprefix('/Game/')
        for suffix in ['.uasset','.uexp','.ubulk']:
            source=(P/'Content'/package).with_suffix(suffix)
            if not source.exists():continue
            target=(R/'Before'/package).with_suffix(suffix);target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():shutil.copy2(source,target)
            result['backups'][str(source)]={'copy':str(target),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    receipt=R/'head_metadata.json';receipt.write_text(json.dumps(result,indent=2));print('BACKPACK_HEAD_METADATA_SCOPE',len(visited),len(selected),flush=True)
    skeletons=[u.load_asset(p) for p,k in selected.items() if k=='Skeleton']
    for path,kind in sorted(selected.items(),key=lambda pair:pair[1]=='Skeleton'):
        asset=u.load_asset(path)
        if not asset:raise RuntimeError('Missing head animation dependency: '+path)
        source=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=result['backups'][str(source)]['sha256']:raise RuntimeError('Concurrent dependency edit: '+path)
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Cannot resave head dependency: '+path)
        result['saved'].append(path);receipt.write_text(json.dumps(result,indent=2));print('BACKPACK_HEAD_METADATA_SAVED',kind,path,flush=True)
        del asset
    result['completed']=True;receipt.write_text(json.dumps(result,indent=2))
main()
gc.collect();u.SystemLibrary.collect_garbage()
