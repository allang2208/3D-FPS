"""Extract the requested inventory view and three masked modeling inputs."""
from pathlib import Path
from PIL import Image
from rembg import remove, new_session
P=Path(__file__).parent
source=Image.open(P/'magic_scroll_source.png').convert('RGB')
session=new_session('u2net')
sheet=Image.new('RGBA',source.size)
for i,name in enumerate(['front','right','back']):
    view=source.crop((i*512,0,(i+1)*512,1024))
    cut=remove(view,session=session)
    cut.save(P/(name+'.png'))
    sheet.paste(cut,(i*512,0))
sheet.save(P/'magic_scroll_three_views.png')
front=Image.open(P/'front.png')
front=front.crop(front.getchannel('A').getbbox())
front=front.rotate(-35,Image.Resampling.BICUBIC,expand=True)
front.thumbnail((448,448),Image.Resampling.LANCZOS)
icon=Image.new('RGBA',(512,512));icon.paste(front,((512-front.width)//2,(512-front.height)//2))
icon.save(P/'magic_scroll_realistic_v1.png')
print('Extracted RGBA views and icon', icon.getchannel('A').getextrema())
