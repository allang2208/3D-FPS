from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent/'Review'
for family in ('skeleton_base','skeleton_mag10_balanced'):
    for view in ('grip','palm'):
        sheet=Image.new('RGB',(1280,3*445),(23,27,33));draw=ImageDraw.Draw(sheet)
        for j,t in enumerate((.08,.15,.25,.325,.55,.65)):
            x=j%2*640;y=j//2*445
            sheet.paste(Image.open(O/family/f'{t:.3f}_{view}.png'),(x,y+25));draw.text((x+10,y+6),f'{family} | {t:.3f}s',fill='white')
        sheet.save(O/f'{family}_{view}.jpg',quality=85)
