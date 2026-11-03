from pathlib import Path
import hashlib,json,zipfile
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
sources=[R/'FPSGAME.uproject']
for base in ('Source','Config'):
    sources.extend(p for p in (R/base).rglob('*') if p.is_file())
sources.extend((R/'Content/ColdSteelData').glob('*.json'))
rows=[]
with zipfile.ZipFile(O/'source-config-recovery.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(sources)):
        data=p.read_bytes();rel=p.relative_to(R).as_posix();z.writestr(rel,data)
        rows.append(dict(path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(scope='local working-source and data-catalog snapshot, including existing shared work; not a published clean Git checkout or a media backup',files=rows,
    content_target=str((R/'Content').resolve()),asset_preflight='dependency-preflight.json',archive='source-config-recovery.zip',
    active_asset_recipes={'guan_lei':'GuanLeiClosedCrownV12/MeshyV13','ji_lei':'JiLeiInlaidLightningV14/MeshyV15','reinforced_and_laminated':'CommonSeatsStructuralV7','light':'LightSeatWindowFixV8','charge_audio':'JiLeiRecordedCurrentV2/MS_JiLei_CurrentRandom'},
    restore_warning='Do not overwrite a live shared workspace from this archive. Restore in a new directory, restore matching local media/plugins, then compile and validate.')
(O/'recovery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Recovery snapshot',len(rows),'files,',(O/'source-config-recovery.zip').stat().st_size,'bytes')
