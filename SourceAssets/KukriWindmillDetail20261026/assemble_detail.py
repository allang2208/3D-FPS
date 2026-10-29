import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent;version=sys.argv[1]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for label in ('jason','kaitlin'):
    times=np.load(OUT/f'{label}-{version}-detail.npz')['times']
    for side in 'rl':
        for phase,ids in [('deploy',[1,2,3,4,5,6]),('return',[8,10,11,12,13,15])]:
            sheet=Image.new('RGB',(6*350,2*385),(20,25,32));draw=ImageDraw.Draw(sheet)
            for row,view in enumerate(('palm','back')):
                for col,k in enumerate(ids):
                    im=Image.open(OUT/'DetailFrames'/f'{label}-{version}-{side}-{view}-{k:02d}.png').resize((350,350))
                    x=col*350;y=row*385
                    title='isolated palm' if view=='palm' else 'back / full skin'
                    sheet.paste(im,(x,y+35));draw.text((x+8,y+6),f'{side.upper()} {title} {times[k]:.3f}s',font=font,fill='white')
            sheet.save(OUT/f'{label}-{version}-{side}-{phase}.jpg',quality=94)
print('DETAIL_SHEETS_COMPLETE',version)
