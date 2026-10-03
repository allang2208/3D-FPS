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
# 2026-10-01 起卷轴占格 1×2 竖直：图标画幅按占格推导为 512×1024 透明底，
# 正面竖直摆放、主轴填满约 91%、轮廓中心对齐画幅中心（与木材 1×2 口径一致）。
height=int(round(1024*.91));width=int(round(front.width*height/front.height))
front=front.resize((width,height),Image.Resampling.LANCZOS)
icon=Image.new('RGBA',(512,1024));icon.paste(front,((512-width)//2,(1024-height)//2),front)
icon.save(P/'magic_scroll_realistic_v1.png')
print('Extracted RGBA views and icon', icon.getchannel('A').getextrema())
