import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3];HOST=P.parent/'ImportProject'
fit=json.loads((P/'fit.json').read_text('utf-8'))
surfaces=json.loads((ROOT/'SourceAssets/KukriRefinement20261027/surfaces.json').read_text('utf-8'))
packages=set()
for e in surfaces['variants']:
    if e['id'] not in {p['id'] for p in fit['parts']}:continue
    packages.add(e['material'].split('.')[0])
    for path in e['textures'].values():packages.add(e['texture_root']+'/'+Path(path).stem)
catalog=json.loads((ROOT/'Content/ColdSteelData/tactical-hatchet-modules.json').read_text('utf-8'))
packages.update(s['mesh'].split('.')[0] for s in catalog['slots']['pommel'].values())
for package in packages:
    rel=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    dest=HOST/'Content'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'Content'/rel,dest)
(HOST/'Config').mkdir(exist_ok=True)
(HOST/'Config/DefaultEngine.ini').write_text('[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n',encoding='utf-8')
(P/'staged_dependencies.json').write_text(json.dumps(sorted(packages),indent=2),encoding='utf-8')
print('DEPENDENCIES_STAGED count='+str(len(packages)))
