"""Copy the exact installed Epic mannequin dependencies needed for the motion candidate."""
from pathlib import Path
import re,json,shutil,hashlib
PROJECT=Path('D:/FPS3D/FPSGAME')
SOURCE=Path('E:/Program Files (x86)/UE_5.8/Templates/TemplateResources/High/Characters/Content')
OUT=PROJECT/'SourceAssets/WitchFoundation20260920'
OUT.mkdir(parents=True,exist_ok=True)
pending=['Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd','Mannequins/Anims/Unarmed/MM_Idle','Mannequins/Meshes/SKM_Quinn_Simple']
done=set();report=[]
while pending:
    rel=pending.pop()
    if rel in done:continue
    done.add(rel)
    file=SOURCE/(rel+'.uasset')
    if not file.exists():raise RuntimeError('Missing template dependency: '+str(file))
    raw=file.read_bytes();dest=PROJECT/'Content/Characters'/(rel+'.uasset')
    if dest.exists():
        # Existing project originals belong to their current users.
        report.append({'asset':'/Game/Characters/'+rel,'operation':'reused_existing','source':str(dest)})
        continue
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest)
    report.append({'asset':'/Game/Characters/'+rel,'operation':'copied_template','source':str(file),'sha256':hashlib.sha256(raw).hexdigest()})
    for match in re.findall(rb'/Game/Characters/([A-Za-z0-9_/]+)',raw):
        dep=match.decode()
        if dep not in done and dep not in pending:pending.append(dep)
(OUT/'template_sources.json').write_text(json.dumps({'origin':'Epic UE 5.8 installed Third Person mannequin template; project-local use, not a CC0 redistribution','files':report},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'copied':sum(r['operation']=='copied_template' for r in report),'reused':sum(r['operation']=='reused_existing' for r in report),'manifest':str(OUT/'template_sources.json')}))
