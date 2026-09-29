from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,os
ROOT=Path(__file__).resolve().parent;REV=os.environ.get('SPITTER_INSPECT_REV','V10');folder=ROOT/('Inspect'+REV)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
for role in ['Walk_B','Walk_C','Run_A']:
    files=sorted((folder/role).glob('*.png'));frames=[]
    for i,file in enumerate(files):
        im=Image.new('RGB',(320,424),(22,27,32));d=ImageDraw.Draw(im)
        d.text((10,8),f'{REV} {role}   {i/12:.2f}s',font=font,fill='white');im.paste(Image.open(file),(0,40));frames.append(im)
    frames[0].save(folder/(role+'.gif'),save_all=True,append_images=frames[1:],duration=83,loop=0)
    sheet=Image.new('RGB',(1280,848))
    for j in range(8):sheet.paste(frames[round(j*len(frames)/8)%len(frames)],((j%4)*320,(j//4)*424))
    sheet.save(folder/(role+'_sheet.png'))
data=json.loads((folder/'measurements.json').read_text())
print(json.dumps({r:{'soles':d['soles'],'stats':{n:d['stats'][n] for n in ['Head','LeftLeg','RightLeg','LeftForeArm','RightForeArm']}} for r,d in data.items()},indent=2))
