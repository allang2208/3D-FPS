"""Record only this revision's published destinations before changing them."""
import json,hashlib,zipfile
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]
paths=['/Game/Weapons/M249/SideMagazine20261108/Animations/A_M249_side_'+s for s in ('reload','reload_empty')]
paths+=['/Game/Weapons/M249/Bipod/DA_M249_SupportGrip']+['/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+s for s in ('vertical','canted','prism','angled')]
key='ue_m249_magazine_m249_side_mag_45';paths+=['/Game/ColdSteelData/AttachmentIcons20260913/'+x+key for x in ('','FramedFirearms/')]
baseline={}
if (r/'before.json').exists():raise RuntimeError('Existing revision baseline retained')
with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED) as z:
    for path in paths:
        f=p/'Content'/(path.removeprefix('/Game/')+'.uasset');baseline[path]=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
        if f.exists():z.write(f,str(f.relative_to(p)))
        if key in path:
            image=f.with_suffix('.png')
            if image.exists():z.write(image,str(image.relative_to(p)))
(r/'before.json').write_text(json.dumps(baseline,indent=2))
print('M249 revision destinations recorded')
