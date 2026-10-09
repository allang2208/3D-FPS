from PIL import Image, ImageDraw
from pathlib import Path
O=Path(__file__).parent/'Diagnostics'
for kind, selected, end in [
 ('normal_7',[0,42,74,88,104,114,120,124,126,128,130,134,140,146],146),
 ('empty_7',[0,74,88,114,128,134,146,158,164,170,176,182],182)]:
    sheet=Image.new('RGB',(1600,((len(selected)+3)//4)*250),(35,35,35));d=ImageDraw.Draw(sheet)
    for i,f in enumerate(selected):
        im=Image.open(O/'Frames'/f'{kind}_{f:03d}.png').convert('RGB').resize((400,225))
        x=(i%4)*400;y=(i//4)*250;sheet.paste(im,(x,y))
        d.text((x+10,y+231),f'{kind} | frame {f} | {f/60:.3f}s source',fill='white')
    sheet.save(O/f'{kind}_sheet.jpg',quality=93)
    frames=[]
    for f in range(0,end+1,2):
        im=Image.open(O/'Frames'/f'{kind}_{f:03d}.png').convert('RGB').resize((768,432))
        d=ImageDraw.Draw(im)
        d.text((10,10),'OFFLINE: saved UE poses + camera curve model | 0.85x | diagnostic colors',fill='white')
        d.text((10,27),f'{kind} | frame {f} | no gameplay or clothing layers',fill='white')
        frames.append(im)
    frames[0].save(O/f'{kind}_preview.gif',save_all=True,append_images=frames[1:],duration=39,loop=0)
print('PREVIEWS_WRITTEN')
