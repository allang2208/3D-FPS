"""Publish private packages, then atomically swap the village while its package is unloaded.

Run in the existing editor's MCP Python batch when present, or inside the production
commandlet. The caller holds the UE batch mutex for the entire operation.
"""
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
try:
    import unreal as u
except ImportError:
    u=None  # No editor is open; Run.ps1 holds the same batch mutex.

root=Path(__file__).resolve().parents[4]
content=(root/'Content').resolve()
batch=content.parent/'ArtProduction/HillsVillageShops/CarpenterYard-20261122'
staged=json.loads((batch/'staged.json').read_text(encoding='utf-8'))
saved=Path(staged['snapshot'])
level=staged['level']
map_rel=Path(level.removeprefix('/Game/')+'.umap')
dest_map=content/map_rel
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def loaded(package):
    return u is not None and (u.find_object(None,package) is not None or
                              u.find_object(None,package+'.'+package.rsplit('/',1)[-1]) is not None)
def install(source,dest,replace=False):
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_name(dest.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        shutil.copyfile(source,temp)
        if replace:
            if sha(dest)!=staged['map_before']:raise RuntimeError('Village revision changed')
            os.replace(temp,dest)
        else:
            os.rename(temp,dest)
    finally:
        if temp.exists():temp.unlink()

current=sha(dest_map)
if current not in (staged['map_before'],staged['map_after']):
    raise RuntimeError('Production village has newer work; stage the current revision.')
paths=[staged['material']]+[row['package'] for row in staged['meshes']]
copies=[]
for pkg in paths:
    rel=Path(pkg.removeprefix('/Game/')+'.uasset')
    source,target=saved/rel,content/rel
    if target.exists():
        if sha(source)!=sha(target):raise RuntimeError('Different production package at '+pkg)
    elif loaded(pkg):
        raise RuntimeError('Unsaved asset is open: '+pkg)
    else:
        copies.append((source,target))
if current!=staged['map_after'] and loaded(level):
    raise RuntimeError('Village package is in use. Publish when it is unloaded.')
if sha(saved/dest_map.name)!=staged['map_after'] or sha(Path(staged['backup']))!=staged['map_before']:
    raise RuntimeError('Staged village or its recovery copy has changed')
for source,target in copies: install(source,target)
if current!=staged['map_after']: install(saved/dest_map.name,dest_map,True)
if u is not None:
    registry=u.AssetRegistryHelpers.get_asset_registry()
    registry.scan_modified_asset_files([str(content/(p.removeprefix('/Game/')+'.uasset')) for p in paths]+[str(dest_map)])
receipt=dict(staged,production_map=str(dest_map),published_packages=paths)
(batch/'published.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('CARPENTER_YARD_PUBLISHED '+str(batch/'published.json'))
