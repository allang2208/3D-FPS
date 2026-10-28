import json,hashlib,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];HOST=P/'StagingHost'
(HOST/'Config').mkdir(parents=True,exist_ok=True)
(HOST/'KukriRefinement.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
    {'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]},indent=2),encoding='utf-8')
(HOST/'Config/DefaultEngine.ini').write_text('[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n',encoding='utf-8')
surfaces=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
icons=json.loads((P/'icon-manifest.json').read_text(encoding='utf-8'))
packages=set();dependencies=set()
for e in surfaces['variants']:
    packages.update(e['texture_root']+'/'+Path(f).stem for f in e['textures'].values())
    if 'dynamics' in e:packages.update([e['mesh'].split('.')[0],e['material'].split('.')[0]])
rune_root='/Game/Weapons/Kukri20261020/ComponentVariants20261026/Runes'
for kind in ('Factory','Swift','HeavyBack','FoldedBalanced'):packages.add(rune_root+'/Materials/M_KukriMark_'+kind)
for suffix in ('BaseColor','ORM','Normal'):dependencies.add('/Game/Weapons/Kukri20261020/Textures/T_Kukri_'+suffix)
for kind in ('RuneWing','RuneKnot','RunePeaks'):dependencies.add(rune_root+'/Textures/T_KukriMask_'+kind)
packages.update(b['texture'].split('.')[0] for b in icons['bindings'])
baseline=[]
for package in sorted(packages|dependencies):
    relative=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    target=ROOT/'Content'/relative;staged=HOST/'Content'/relative
    if target.exists():
        staged.parent.mkdir(parents=True,exist_ok=True)
        if staged.exists():raise RuntimeError('Staging already exists '+str(staged))
        shutil.copy2(target,staged)
    elif package in dependencies:raise RuntimeError('Dependency missing '+package)
    if package in packages:baseline.append({'package':package,'target':str(target),'staged':str(staged),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None})
for b in icons['bindings']:
    target=Path(b['runtime_png'])
    baseline.append({'package':b['texture'],'target':str(target),'staged':str(P/'Icons'/(b['master']+'.png')),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None})
(P/'Receipts/staging-inputs.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
print('KUKRI_REFINEMENT_TARGET_PACKAGES '+str(len(packages)))
