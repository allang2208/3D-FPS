import json,hashlib,shutil,zipfile,datetime
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME'); W=Path(__file__).resolve().parent; R=P/'SourceAssets/WoodworkingBenchV4'
assert not (R/'GameReady').exists(), 'Game-ready work already exists; inspect first'
paths=['Source/FPSGAME/Building/VoxelBuildPrefabActor.cpp','Source/FPSGAME/UI/ColdSteelWoodworkingWidget.cpp','Source/FPSGAME/UI/ColdSteelWoodworkingWidget.h','Tools/Building/register_woodworking_bench.py','Content/ColdSteelData/woodworking.json','SourceAssets/WoodworkingBenchV2/registration.json']
paths += [str(p.relative_to(P)).replace('\\','/') for p in (P/'Content/Building/WoodworkingBenchV2').rglob('*') if p.is_file()]
paths += ['Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset']
baseline={}
for rel in paths:
    p=P/rel
    if not p.is_file(): continue
    target=W/'Before'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(p,target)
    baseline[rel]={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'size':target.stat().st_size}
for name in ['WoodworkingBench_Core.zip','WoodworkingBench_Textures_01.zip','WoodworkingBench_Textures_02.zip']:
    p=P/'SourceAssets/WoodworkingBenchV2/Input'/name
    assert p.is_file(),p
    target=R/'Input'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    with zipfile.ZipFile(target) as z:
        for item in z.infolist():
            output=(R/'Source'/item.filename).resolve();assert output.is_relative_to((R/'Source').resolve())
        z.extractall(R/'Source')
core=R/'Input/WoodworkingBench_Core.zip'
assert hashlib.sha256(core.read_bytes()).hexdigest()=='1153eadc9aea9b22edb40b46da816b437b5cd1b022f25a09a074f9cea0941781'
assert json.loads((R/'Source/WoodworkingBench/v4_manifest.json').read_text())['version']==4
(W/'baseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
(W/'source_receipt.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'core_sha256':hashlib.sha256(core.read_bytes()).hexdigest(),'backed_up_files':len(baseline),'source':str(R/'Source/WoodworkingBench/WoodworkingBench_Editable.blend')},indent=2))
print('SOURCE_PREPARED',len(baseline),'backup files',R)
