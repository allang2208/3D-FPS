from pathlib import Path
from PIL import Image,ImageDraw
import json
OUT=Path(__file__).resolve().parent
frames=[Image.open(OUT/('preview_run_%02d.png'%i)).convert('RGB') for i in range(1,21)]
frames[0].save(OUT/'HundredEyedSlag_RunV2.gif',save_all=True,append_images=frames[1:],duration=[30,30,40]*6+[30,30],loop=0)
sheet=Image.new('RGB',(1440,1080),(20,22,25));draw=ImageDraw.Draw(sheet)
for index,frame in enumerate([1,6,11,16]):
    sheet.paste(frames[frame-1],((index%2)*720,(index//2)*540))
sheet.save(OUT/'HundredEyedSlag_RunV2_contacts.jpg',quality=92)
death=Image.new('RGB',(1800,300),(20,22,25))
for index,frame in enumerate([1,4,7,10,14]):
    image=Image.open(OUT/('preview_death_%02d.png'%frame)).resize((360,270))
    death.paste(image,(index*360,30));ImageDraw.Draw(death).text((index*360+10,8),'%.2fs'%((frame-1)/30),fill='white')
death.save(OUT/'HundredEyedSlag_DeathV2_handoff.jpg',quality=92)
data=json.loads((OUT/'contact_analysis.json').read_text())
summary={}
for role in ('Run','Move'):
    rows=data[role];summary[role]={'max_reach_error_cm':max(f['reach_error_m']*100 for r in rows for f in r['feet'].values()),
        'max_planted_pad_height_error_cm':max(abs(f['pad_z_m'])*100 for r in rows for f in r['feet'].values() if f['stance'])}
summary['authoring_rendered']=True;summary['game_runtime_tested']=False
(OUT/'authoring_checks.json').write_text(json.dumps(summary,indent=2))
