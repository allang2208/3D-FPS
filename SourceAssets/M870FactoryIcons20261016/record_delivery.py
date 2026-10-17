"""Record the generated/deployed icons and actual UE save receipt."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
deployment=json.loads((OUT/'deployment.json').read_text())
saved=json.loads((OUT/'import_receipt.json').read_text())
if not saved['completed']:raise RuntimeError('Texture import has not completed; retain partial save receipt')
files=[]
for item in deployment['entries']:
    png=ROOT/item['runtime_png'];package=png.with_suffix('.uasset')
    files.append({'key':item['key'],'png':str(png.relative_to(ROOT)),'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),
        'package':str(package.relative_to(ROOT)),'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest()})
report={'created_utc':datetime.now(timezone.utc).isoformat(),'weapon':'ue_m870','generated_images':5,'reused_existing_images':1,'factory_keys':len(files),
    'generation':'Built-in imagegen with actual-model component references and approved metal frame',
    'prompt_manifest':'generation_manifest.json','files':files,'ue_save':saved,
    'cpp_changed':False,'native_build_required':False,'game_or_pie_started':False,
    'runtime_visual_acceptance':'Pending user test; reopen the modification panel to reload icons'}
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'saved':'delivery.json','generated_images':5,'runtime_pngs':len(files),'saved_ue_textures':len(saved['saved'])}))
