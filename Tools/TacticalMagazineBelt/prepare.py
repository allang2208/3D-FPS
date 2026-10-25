"""Freeze the current saved ST6 waist geometry and native body binding sources."""
import hashlib
import json
import shutil
from pathlib import Path

P=Path(__file__).resolve().parents[2];R=P/'SourceAssets/TacticalMagazineBelt20261024'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for folder in ('Inputs','Exports','Authored','Textures','Reference','Logs'):(R/folder).mkdir(parents=True,exist_ok=True)
cfg=read(P/'Content/ColdSteelData/modular_outfits.json');body=read(P/'Content/ColdSteelData/player_body.json')
captured=read(P/'SourceAssets/BackpackFit20261024/ContactFitR3/captured.json')
male=read(P/'SourceAssets/KaitlinPlayer20261023/FitInputs/captured.json')[body['body_mesh']]['file']
sources={'Jason':P/'SourceAssets/KaitlinPlayer20261023/FitInputs'/male,'Kaitlin':P/'SourceAssets/KaitlinPlayer20261023/NativeGeometry/MHC_Kaitlin_Body.json'}
rows=[]
for name,c in [('Jason',cfg),('Kaitlin',cfg['body_variants']['kaitlin'])]:
    path=c['items']['ue_st6_tactical_pants']['rig_meshes'][name];record=captured[path]
    package=P/'Content'/(path.split('.')[0][6:]+'.uasset')
    if sha(package)!=record['package_sha256']:raise RuntimeError('Refresh the current pants geometry before authoring '+name)
    folder=Path(record['folder'])
    for kind in ('positions','triangles'):shutil.copy2(folder/(kind+'.bin'),R/'Inputs'/f'{name}_{kind}.bin')
    native=R/'Inputs'/f'{name}_NativeBody.json';shutil.copy2(sources[name],native)
    rows.append(dict(body=name,pants_asset=path,package_sha256=record['package_sha256'],capture_folder=str(folder),native_reference=str(native),native_reference_sha256=sha(native)))
concept=P/'SourceAssets/TacticalMagazineBeltDesign20261024/tactical-magazine-belt-concept-v1.png'
shutil.copy2(concept,R/'Reference/approved-concept.png')
(R/'inputs.json').write_text(json.dumps(dict(records=rows,pants_reference='ue_st6_tactical_pants',approved_concept=str(concept),runtime_tested=False),indent=2)+'\n',encoding='utf-8')
print('BELT_NATIVE_INPUTS_FROZEN',len(rows),flush=True)
