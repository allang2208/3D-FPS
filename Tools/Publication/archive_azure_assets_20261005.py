"""Move only the checked retired Azure packages, inside the editor's existing batch gate."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
RECORDS=ROOT/'Docs/Publication/AzureDragon20261005'
ARCHIVE=(ROOT/'trash/azure-dragon-retired-20261005').resolve()
CONTENT=(ROOT/'Content/Weapons/AzureDragon20261004').resolve()
plan=json.loads((RECORDS/'archive-plan.json').read_text(encoding='utf-8'))
entries=[e for e in plan['files'] if e['kind']=='asset']
packages={e['package'] for e in entries}
registry=u.AssetRegistryHelpers.get_asset_registry()
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
    include_searchable_names=True,include_soft_management_references=True,include_hard_management_references=True)
dirty={str(p.get_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if packages & dirty:
    raise RuntimeError('Preserve unsaved retired packages: '+str(sorted(packages&dirty)))
loaded=[]
for package in sorted(packages):
    external=[str(r) for r in registry.get_referencers(package,options) if str(r) not in packages]
    if external:
        raise RuntimeError('Preserve externally referenced old package '+package+': '+str(external))
    obj=u.find_object(None,package)
    if obj:
        loaded.append(obj)
if loaded:
    changed,error=u.EditorLoadingAndSavingUtils.unload_packages(loaded)
    if str(error):
        raise RuntimeError('Cannot unload old packages safely: '+str(error))
loaded=None
obj=None
u.SystemLibrary.collect_garbage()
for package in sorted(packages):
    if u.find_object(None,package):
        raise RuntimeError('Preserve an old package still held by a live object: '+package)
moves=[]
for e in entries:
    source=(ROOT/e['source']).resolve()
    target=(ROOT/e['destination']).resolve()
    if not source.is_relative_to(CONTENT) or not target.is_relative_to(ARCHIVE):
        raise RuntimeError('Archive path leaves the task scope')
    if target.exists() or source.stat().st_size!=e['bytes'] or hashlib.sha256(source.read_bytes()).hexdigest()!=e['sha256']:
        raise RuntimeError('Preserve changed source or existing archive '+str(source))
    moves.append((e,source,target))
result=dict(complete=False,files=[])
for e,source,target in moves:
    target.parent.mkdir(parents=True,exist_ok=True)
    source.rename(target)
    e['readback_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    result['files'].append(e)
    (RECORDS/'asset-archive.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if e['readback_sha256']!=e['sha256']:
        raise RuntimeError('Archive readback mismatch '+str(target))
registry.scan_paths_synchronous(['/Game/Weapons/AzureDragon20261004/'+f for f in ('RigV2','EnergyV3','EnergyV6','Meshes')],True)
result['complete']=True
(RECORDS/'asset-archive.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('AZURE_ASSETS_ARCHIVED files='+str(len(entries))+' readbacks_equal=true editor_preserved=true')
