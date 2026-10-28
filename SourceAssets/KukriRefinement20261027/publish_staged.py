"""Publish this exact texture/mesh/material set and merge current catalog fields."""
import json,hashlib,shutil,os
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
for file in ('import-surfaces.json','import-icons.json'):
    if not json.loads((P/'Receipts'/file).read_text(encoding='utf-8'))['complete']:raise RuntimeError('Incomplete authoring '+file)
jobs=json.loads((P/'Receipts/staging-inputs.json').read_text(encoding='utf-8'))
for row in jobs:
    target=Path(row['target']);source=Path(row['staged'])
    actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    if actual!=row['sha256']:raise RuntimeError('Concurrent target edit preserved: '+str(target))
    if not source.exists():raise RuntimeError('Saved production output missing: '+str(source))
receipt={'complete':False,'started':datetime.now().astimezone().isoformat(),'files':[],'catalogs':[],
         'runtime_tested':False,'numeric_changes':False,'native_build':'FPSGAMEEditor Development succeeded; build-editor.log'}
def record():
    (P/'Receipts/publication.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
for row in jobs:
    target=Path(row['target']);source=Path(row['staged']);target.parent.mkdir(parents=True,exist_ok=True)
    backup=P/'Before/Content'/target.relative_to(ROOT/'Content')
    if target.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
    temporary=target.with_name(target.name+'.kukri-refine-'+str(os.getpid())+'.tmp')
    shutil.copy2(source,temporary);os.replace(temporary,target)
    receipt['files'].append({'target':str(target),'source':str(source)})
    record()
data=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
variants={e['id']:e for e in data['variants']}
def merge(path,edit):
    original=path.read_bytes();value=json.loads(original.decode('utf-8-sig'));edit(value)
    backup=P/'Before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(original)
    if path.read_bytes()!=original:raise RuntimeError('Concurrent catalog edit preserved: '+str(path))
    temp=path.with_name(path.name+'.kukri-refine.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)
    receipt['catalogs'].append(str(path));record()
def modules(value):
    value['surface_revision']='KukriRefinement20261027'
    for e in data['variants']:
        if 'runtime_dynamics' not in e:continue
        spec=value['slots']['lanyard'][e['id']]
        name=e['material'].rsplit('.',1)[-1]
        spec.update(e['runtime_dynamics']);spec.update(mesh=e['mesh'],material_slot_names=[name],materials={name:e['material']},
            physics='SwordTasselMeshComponent: bounded gravity, inertia, damping and length constraints')
merge(ROOT/'Content/ColdSteelData/kukri-modules.json',modules)
def component_manifest(value):
    for old in value['variants']:
        if old['id'] not in variants:continue
        new=variants[old['id']]
        for field in ('textures','object','mesh','material','fbx','source_blend','icon_input','icon'):
            if field in new:old[field]=new[field]
        old['surface_revision']='KukriRefinement20261027'
merge(P.parent/'KukriComponentVariants20261026/components.json',component_manifest)
merge(P.parent/'KukriBladeSurfaceV220261026/surfaces.json',component_manifest)
icon_manifest=json.loads((P/'icon-manifest.json').read_text(encoding='utf-8'))
def icons(value):
    masters={m['id']:m for m in icon_manifest['masters']}
    for master in value['masters']:
        if master['id'] in masters:master.update(masters[master['id']])
    value['rendering']=icon_manifest['rendering'];value['frame_reference']=str(P/'StandardEmptyFrame.png')
merge(P.parent/'KukriFinalIntegration20261026/manifest.json',icons)
receipt.update(complete=True,texture_packages=65,material_packages=8,mesh_packages=4,icon_masters=20,icon_bindings=26)
record();print('KUKRI_REFINEMENT_PUBLISHED '+str(len(receipt['files']))+' files')
