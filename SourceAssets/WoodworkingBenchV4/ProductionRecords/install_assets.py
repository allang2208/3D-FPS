import json,hashlib,shutil,datetime
from pathlib import Path
W=Path(__file__).resolve().parent;P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/WoodworkingBenchV4';H=W/'ImportHost/Content/Building/WoodworkingBenchV4';D=P/'Content/Building/WoodworkingBenchV4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((W/'ue_import_receipt.json').read_text());baseline=json.loads((W/'baseline.json').read_text())
assert receipt['lod_screen_sizes_set_after_final_mesh_build']
assert json.loads((W/'finalize_exit.json').read_text())['exitCode']==0
assert receipt['source_manifest_sha256']==sha(R/'Source/WoodworkingBench/v4_manifest.json')
files=sorted(f for f in H.rglob('*') if f.is_file())
assert len(files)==29,len(files)
for src in files:assert src.suffix in {'.uasset','.ubulk','.uexp'} and not (D/src.relative_to(H)).exists(),src
helper='Tools/Building/register_woodworking_bench.py';assert sha(P/helper)==baseline[helper]['sha256']
ledger=[]
for src in files:
    dst=D/src.relative_to(H);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
    ledger.append({'path':str(dst.relative_to(P)).replace('\\','/'),'sha256':sha(dst),'bytes':dst.stat().st_size})
s=(P/helper).read_text(encoding='utf-8-sig').replace('WoodworkingBenchV2','WoodworkingBenchV4').replace('V2','V4')
(P/helper).write_text(s,encoding='utf-8')
config={'revision':'V4','ready_for_registration':True,'mesh':'/Game/Building/WoodworkingBenchV4/SM_WoodworkingBench','source_manifest':'Source/WoodworkingBench/v4_manifest.json','menu_category':'other','material_group':'','blade_mesh':'/Game/Building/WoodworkingBenchV4/SM_WoodworkingSawBlade','body_mesh':'/Game/Building/WoodworkingBenchV4/SM_WoodworkingBenchBody','note':'V4 full mother imported. Merged preview preserves blade before async body swap. Gameplay and visual acceptance not run.'}
(R/'registration.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'assets':ledger,'registration_helper_sha256':sha(P/helper),'palette_modified':False}
(W/'installed_assets.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('V4_ASSETS_INSTALLED',len(ledger),sum(x['bytes'] for x in ledger))
