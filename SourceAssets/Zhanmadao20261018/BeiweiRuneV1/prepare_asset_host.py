"""Copy only the required material dependency closure to an isolated editor-only host."""
import json,re,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];H=P/'AssetHost';H.mkdir(exist_ok=True)
catalog=json.loads((ROOT/'Content/ColdSteelData/zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
roots=[]
source_file=P/'source_bindings.json'
if source_file.exists():
    for materials in json.loads(source_file.read_text(encoding='utf-8')).values():roots.extend(materials.values())
else:
    for part in catalog['slots']['blade_1'].values():roots.extend(part.get('materials',{}).values())
pending=[path.split('.')[0] for path in roots];copied={}
pending.extend(path.split('.')[0]+'_Whirlwind' for path in roots)
while pending:
    package=pending.pop()
    if package in copied:continue
    if not re.fullmatch(r'/Game/[A-Za-z0-9_/]+',package):continue
    relative=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    source=ROOT/'Content'/relative
    if not source.exists():continue
    target=H/'Content'/relative;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target);copied[package]=str(source)
    for suffix in ['.uexp','.ubulk','.uptnl']:
        companion=source.with_suffix(suffix)
        if companion.exists():shutil.copy2(companion,target.with_suffix(suffix))
    data=source.read_bytes()
    pending.extend(path.decode('ascii').split('.')[0] for path in re.findall(rb'/Game/[A-Za-z0-9_/\.]+',data))
project={'FileVersion':3,'EngineAssociation':'5.8','Description':'Isolated Zhanmadao material authoring; no game module',
    'Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}
(H/'AssetHost.uproject').write_text(json.dumps(project,indent=2)+'\n',encoding='utf-8')
config=(ROOT/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
renderer=re.search(r'(?ms)^\[/Script/Engine.RendererSettings\]\s*\n.*?(?=^\[|\Z)',config)
(H/'Config').mkdir(exist_ok=True)
(H/'Config/DefaultEngine.ini').write_text((renderer.group(0) if renderer else '')+'\n[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n',encoding='utf-8')
(P/'asset_host_sources.json').write_text(json.dumps({'project':str(H/'AssetHost.uproject'),'packages':copied},indent=2)+'\n',encoding='utf-8')
print('ISOLATED_ASSET_HOST_READY',len(copied))
