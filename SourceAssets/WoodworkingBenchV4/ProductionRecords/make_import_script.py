from pathlib import Path
import json
W=Path(__file__).resolve().parent;old=W.parent/'woodworking_v2_import_20261007'
s=(old/'ue_import.py').read_text();s=s[:s.index('task=u.AssetImportTask();task.filename=str(S/')]
s=s.replace('woodworking_v2_import_20261007','woodworking_v4_import_20261008').replace('WoodworkingBenchV2','WoodworkingBenchV4').replace('WoodworkingV2Import','WoodworkingV4Import')
s=s.replace("W/'ImportHostFinal'","W/'ImportHost'")
s+=(W/'ue_import_meshes.py').read_text()
(W/'ue_import.py').write_text(s,encoding='utf-8')
host=W/'ImportHost';host.mkdir(exist_ok=True)
project=json.loads((old/'ImportHostFinal/WoodworkingImport.uproject').read_text());project['Description']='Isolated V4 woodworking asset authoring host'
(host/'WoodworkingImport.uproject').write_text(json.dumps(project,indent=2))
p=(old/'run_import_final.ps1').read_text().replace('woodworking_v2_import_20261007','woodworking_v4_import_20261008').replace('ImportHostFinal','ImportHost').replace('WoodworkingV2Import','WoodworkingV4Import').replace('import_final','import')
(W/'run_import.ps1').write_text(p,encoding='utf-8')
print('IMPORT_SCRIPT_READY')
