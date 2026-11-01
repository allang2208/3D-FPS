from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent;frames=[]
for i in range(55):
    frame=Image.new('RGB',(960,386),(23,27,32))
    frame.paste(Image.open(O/'Preview'/f'{i:03d}_fps.png').convert('RGB'),(0,26))
    frame.paste(Image.open(O/'Preview'/f'{i:03d}_hand.png').convert('RGB').resize((320,180)),(640,116))
    d=ImageDraw.Draw(frame)
    d.text((10,8),f'M24 club regrip - source motion, 0.5x speed    {i/60:.3f}s',fill='white')
    d.text((675,95),'Right-hand grip detail',fill='white')
    d.text((657,318),'UE camera feedback not shown',fill=(180,185,190))
    frames.append(frame)
frames[0].save(O/'M24_ClubRegrip_Preview.gif',save_all=True,append_images=frames[1:],duration=[33]*54+[700],loop=0,optimize=True)
print('M24_CLUB_GIF_READY')
