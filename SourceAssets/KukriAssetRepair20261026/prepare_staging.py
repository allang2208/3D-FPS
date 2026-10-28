"""Copy only this Kukri batch into an isolated asset authoring host."""
import json,hashlib,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
project=P.parents[1]
host=P/'StagingHost'
host.mkdir(exist_ok=True)
uproject={'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
    {'Name':'PythonScriptPlugin','Enabled':True},
    {'Name':'EditorScriptingUtilities','Enabled':True}]}
(host/'KukriAssetAuthoring.uproject').write_text(json.dumps(uproject,indent=2),encoding='utf-8')
(host/'Config').mkdir(exist_ok=True)
(host/'Config/DefaultEngine.ini').write_text('[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n',encoding='utf-8')
blades=json.loads((P.parent/'KukriBladeSurfaceV220261026/surfaces.json').read_text(encoding='utf-8'))['variants']
parts=json.loads((P.parent/'KukriComponentVariants20261026/components.json').read_text(encoding='utf-8'))['variants']
packages=set()
for e in blades+parts:
    packages.update([e['mesh'].split('.')[0],e['material'].split('.')[0]])
    folder=e['mesh'].split('.')[0].rsplit('/',1)[0]
    packages.update(folder+'/Textures/'+Path(f).stem for f in e['textures'].values())
manifest=[]
for package in sorted(packages):
    relative=Path(package.removeprefix('/Game/'))
    for suffix in ('.uasset','.uexp','.ubulk'):
        source=(project/'Content'/relative).with_suffix(suffix)
        if not source.exists():
            if suffix=='.uasset':raise RuntimeError('Source missing: '+str(source))
            continue
        target=(host/'Content'/relative).with_suffix(suffix)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():raise RuntimeError('Staging asset already exists: '+str(target))
        shutil.copy2(source,target)
        manifest.append({'package':package,'source':str(source),'staged':str(target),
                         'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
(P/'staging-inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('KUKRI_STAGING_INPUTS_COPIED '+str(len(manifest)))
