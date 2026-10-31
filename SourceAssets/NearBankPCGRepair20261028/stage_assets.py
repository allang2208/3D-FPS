"""Select the dependency closure of actual output, reusing installed library assets.
Run under the shared UE batch mutex. Never copy source maps or the full sample.
"""
from pathlib import Path
from datetime import datetime
import json,shutil,hashlib,sys
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
HOST=R/'AuthoringHost';SAMPLE=PROJECT/'城市示例'
manifest=json.loads((R/'native_manifest.json').read_text())
deps=json.loads((R/'native_dependencies.json').read_text())

def pkg(p):return p.split('.')[0]
def disk(root,p):return root/(p+'.uasset')
def reuse(p):
    if not p:return None
    if p.startswith('/Game/') and not p.startswith('/Game/NativeNearBank20261028/'):
        alt='/Game/CitySampleBuildings/'+p[len('/Game/'):]
        if disk(PROJECT/'Content',pkg(alt)[len('/Game/'):]).is_file():return alt
    return p

required=set();reuse_map={}
for row in manifest['rows']:
    for key in ['mesh','materials']:
        values=[row[key]] if key=='mesh' else row[key]
        mapped=[reuse(v) for v in values]
        for old,new in zip(values,mapped):
            if old and new!=old:reuse_map[old]=new
            if new:required.add(pkg(new))
        row[key]=mapped[0] if key=='mesh' else mapped
closure=set();pending=list(required)
while pending:
    p=pending.pop()
    if p in closure or p.startswith(('/Engine/','/Script/')):continue
    closure.add(p)
    if p.startswith('/Game/CitySampleBuildings/'):continue
    pending.extend(deps.get(p,[]))

files=[];present=[];missing=[]
for p in sorted(closure):
    if p.startswith('/Game/'):
        relative=p[len('/Game/'):]
        src=disk(HOST/'Content',relative);dst=disk(PROJECT/'Content',relative)
    elif p.startswith('/CitySamplePCG/'):
        relative=p[len('/CitySamplePCG/'):]
        src=disk(SAMPLE/'Plugins/Experimental/CitySamplePCG/Content',relative)
        dst=disk(PROJECT/'Plugins/CitySamplePCG/Content',relative)
    elif p.startswith('/Traffic/'):
        relative=p[len('/Traffic/'):]
        src=disk(SAMPLE/'Plugins/Traffic/Content',relative)
        dst=disk(PROJECT/'Plugins/Traffic/Content',relative)
    else:
        # Engine-provided content mounts are available in the same UE version.
        if p.startswith(('/PCG/','/PCGPrimitives/','/Niagara/','/SpeedTreeImporter/')):continue
        missing.append(dict(package=p,reason='Unknown content mount'));continue
    if dst.exists():
        if p.startswith('/Game/NativeNearBank20261028/Meshes/') and src.is_file():
            # Only regeneratable surfaces owned by this generator are replaced.
            backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/'GeneratedSurfaces'/dst.name
            if '--plan-only' not in sys.argv:
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
            files.append(dict(package=p,source=str(src),target=str(dst),bytes=src.stat().st_size,replace_owned_surface=True))
        else:present.append(p)
        continue
    if not src.is_file():missing.append(dict(package=p,source=str(src)));continue
    files.append(dict(package=p,source=str(src),target=str(dst),bytes=src.stat().st_size))
plan=dict(packages=len(closure),reuse=reuse_map,already_present=present,files=files,copy_bytes=sum(x['bytes'] for x in files),missing=missing)
(R/'asset_migration_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
print('SELECTED_ASSET_PLAN',len(files),round(plan['copy_bytes']/1024**3,3),'GiB','reused',len(reuse_map),'unresolved',len(missing),flush=True)
if '--plan-only' in sys.argv:raise SystemExit(0)
if missing:raise RuntimeError('Resolve required packages before migration: '+str(missing[:8]))
plugin=PROJECT/'Plugins/CitySamplePCG/CitySamplePCG.uplugin'
if any(x['package'].startswith('/CitySamplePCG/') for x in files) and not plugin.exists():
    plugin.parent.mkdir(parents=True,exist_ok=True)
    plugin.write_text(json.dumps(dict(FileVersion=3,Version=1,VersionName='1.0',FriendlyName='Selected City Sample PCG Assets',Description='Selected Epic City Sample assets used by the apartment near-bank district. Production graphs remain in SourceAssets.',Category='Content',CanContainContent=True,EnabledByDefault=True,Installed=False),indent=2),encoding='utf8')
traffic=PROJECT/'Plugins/Traffic/Traffic.uplugin'
if any(x['package'].startswith('/Traffic/') for x in files) and not traffic.exists():
    traffic.parent.mkdir(parents=True,exist_ok=True)
    traffic.write_text(json.dumps(dict(FileVersion=3,Version=1,VersionName='1.0',FriendlyName='Selected City Sample Vehicle Material Function',Description='One material function used by static parked vehicles; no traffic simulation modules.',Category='Content',CanContainContent=True,EnabledByDefault=True,Installed=False),indent=2),encoding='utf8')
for f in files:
    src=Path(f['source']);dst=Path(f['target']);dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists() and not f.get('replace_owned_surface'):raise RuntimeError('Destination appeared during production; preserve '+str(dst))
    shutil.copy2(src,dst)
    for ext in ('.uexp','.ubulk','.uptnl'):
        side=src.with_suffix(ext)
        if side.exists():shutil.copy2(side,dst.with_suffix(ext))
manifest['stage']='ready_for_formal_map';manifest['asset_migration_bytes']=plan['copy_bytes']
(R/'publish_manifest.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
(R/'assets_staged.json').write_text(json.dumps(dict(stage='actual_output_assets_copied',packages_copied=len(files),copied_bytes=plan['copy_bytes'],reused_roots=len(reuse_map),saved_at=datetime.now().astimezone().isoformat()),indent=2),encoding='utf8')
print('NATIVE_ASSETS_STAGED',len(files),plan['copy_bytes'],len(reuse_map),flush=True)
