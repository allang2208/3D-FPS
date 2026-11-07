from pathlib import Path
from PIL import Image, ImageDraw

O=Path(__file__).resolve().parent
folder=O/('SavedPreview' if (O/'SavedPreview').exists() else 'After')
for stock,label in (('stock','SKELETON STOCK'),('carbon','CARBON STOCK')):
    frames=[]
    for i in range(55):
        t=i/60
        file=folder/f'skeleton_base_{stock}_{t:.3f}_grip.png'
        im=Image.open(file).convert('RGB').resize((640,448),Image.Resampling.LANCZOS)
        draw=ImageDraw.Draw(im)
        draw.rectangle((0,0,640,28),fill=(18,22,27))
        draw.text((12,9),f'{label}  |  OFFLINE MOTION  |  0.5x  |  {t:.3f}s',fill=(225,230,235))
        frames.append(im)
    frames[0].save(O/f'{stock}_quick_melee.gif',save_all=True,append_images=frames[1:],duration=[33]*54+[400],loop=0,optimize=False)
    print('PREVIEW',stock,flush=True)
