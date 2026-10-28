"""Keep icon masters local and deploy only the new kukri keys."""
import json, shutil
from pathlib import Path
P=Path(__file__).resolve().parent
D=P.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
G=Path(r'C:\Users\allan\.codex\generated_images\01a17715-3312-74c2-a3a3-318b877cf0ca')
masters={
    'blade_1':G/'exec-ddedd964-44af-4f3c-9d21-eace435d267b.png',
    'grip':P/'IconInputs/SM_Kukri_Grip_Factory.png',
    'pommel':P/'IconInputs/SM_Kukri_Pommel_Factory.png',
    'lanyard':G/'exec-5db0ae04-3d62-4f12-8c8b-3e3f3a86c7ab.png',
    'blade_2':D/'rune_false.png'}
out=P/'Icons';out.mkdir(exist_ok=True)
jobs=[]
for slot,source in masters.items():
    master=out/(slot+'.png')
    if not master.exists():shutil.copy2(source,master)
    keys=['ue_kukri_'+slot+'_false','ue_kukri_category_'+slot]
    if slot=='blade_2':keys.append('ue_kukri_lanyard_no_lanyard')
    for key in keys:
        shutil.copy2(master,D/(key+'.png'))
        jobs.append({'key':key,'source':str(master),'runtime_png':str(D/(key+'.png'))})
(P/'icon_deployments.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'icon_provenance.json').write_text(json.dumps({'tool':'built-in image_gen','generated':['blade_1','lanyard'],
    'actual_model_render_fallback':['grip','pommel'],'reason':'Image generation rejected these two requests with category violence; no retries.',
    'shared_existing':['blade_2','no_lanyard'],'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('Kukri icon PNGs deployed:',len(jobs))
