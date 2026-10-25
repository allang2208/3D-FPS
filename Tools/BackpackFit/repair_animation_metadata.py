"""Upgrade saved native body clips/curve metadata before non-editor game loading."""
import gc,hashlib,json,os,re,shutil
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
def main():
    body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    paths=sorted(set(body['clips'].values())|set(body['body_variants']['kaitlin']['clips'].values()))
    before=R/'Before';before.mkdir(exist_ok=True);receipt=R/'animation_metadata.json'
    data={'clips':[],'skeletons':[],'backups':{},'changes':'Serialization version and accumulated curve metadata; no pose/track authoring'}
    def backup(path):
        package=path.split('.')[0].removeprefix('/Game/');base=P/'Content'/package
        if not path.startswith('/Game/'):raise RuntimeError('Only project-owned packages may be resaved: '+path)
        for suffix in ['.uasset','.uexp','.ubulk']:
            source=base.with_suffix(suffix)
            if not source.exists():continue
            target=(before/package).with_suffix(suffix);target.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            if not target.exists():shutil.copy2(source,target)
            data['backups'][str(source)]={'copy':str(target),'sha256':digest}
    skeleton_paths=set()
    for path in paths:
        backup(path)
        asset_data=u.EditorAssetLibrary.find_asset_data(path);tag=asset_data.get_tag_value('Skeleton')
        match=re.search(r"/Game/[^'\"]+",str(tag))
        if not match:raise RuntimeError('Missing skeleton registry tag: '+path+' '+str(tag))
        skeleton_paths.add(match.group(0))
    for path in sorted(skeleton_paths):backup(path)
    receipt.write_text(json.dumps(data,indent=2))
    skeletons=[u.load_asset(path) for path in sorted(skeleton_paths)]
    if any(x is None for x in skeletons):raise RuntimeError('A native skeleton failed to load')
    for index,path in enumerate(paths):
        asset=u.load_asset(path)
        if not isinstance(asset,u.AnimSequence):raise RuntimeError('Expected native animation sequence: '+path)
        source=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=data['backups'][str(source)]['sha256']:raise RuntimeError('Concurrent clip edit: '+path)
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Clip save failed: '+path)
        data['clips'].append(path);receipt.write_text(json.dumps(data,indent=2))
        if index%20==0:print('BACKPACK_NATIVE_METADATA',index+1,len(paths),flush=True)
        del asset
        if index%20==19:gc.collect();u.SystemLibrary.collect_garbage()
    for asset in skeletons:
        path=asset.get_path_name();source=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=data['backups'][str(source)]['sha256']:raise RuntimeError('Concurrent skeleton edit: '+path)
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Skeleton metadata save failed: '+path)
        data['skeletons'].append(path)
    data['completed']=True;receipt.write_text(json.dumps(data,indent=2));print('BACKPACK_NATIVE_METADATA_SAVED',len(data['clips']),len(data['skeletons']),flush=True)
main()
gc.collect();u.SystemLibrary.collect_garbage()
