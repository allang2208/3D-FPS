"""Capture source frames without interpolation; times are original Bilibili P1 times."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import cv2, subprocess,imageio_ffmpeg
p=Path(__file__).resolve().parent/'Reference'
v=cv2.VideoCapture(str(p/'Context_02m49s_to_02m59s.mp4'));fps=v.get(cv2.CAP_PROP_FPS)
def frame(k):
    v.set(cv2.CAP_PROP_POS_FRAMES,k);ok,bgr=v.read()
    if not ok:raise ValueError(k)
    return Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
keys=[(99,'旧枪退场'),(105,'画面清空'),(108,'新枪入镜'),(111,'镜筒上提'),(114,'托住前端'),(117,'接近腰射位'),(120,'小幅回落'),(126,'持枪稳定')]
dst=Image.new('RGB',(4*372,2*239+44),(20,23,26));draw=ImageDraw.Draw(dst)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15);heading=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc',20)
draw.text((10,7),'装备狙击枪  /  原片逐帧    ·    BV1JK421y7Q5',font=heading,fill=(238,240,240))
frames=p/'Keyframes';frames.mkdir(exist_ok=True)
for i,(k,label) in enumerate(keys):
    im=frame(k);ts=169+k/fps;im.save(frames/('ref_%06dms.png'%round(ts*1000)))
    x=i%4*372;y=44+i//4*239
    dst.paste(im.resize((372,210),Image.Resampling.LANCZOS),(x,y))
    draw.text((x+7,y+212),f'02:{ts-120:06.3f}   {label}',font=font,fill=(228,234,236))
dst.save(p/'Equip_keyframes.jpg',quality=92)
images=[]
for k in range(96,130):
    im=frame(k).resize((640,360),Image.Resampling.LANCZOS)
    d=ImageDraw.Draw(im);d.rectangle((5,5,203,32),fill=(20,23,26))
    d.text((12,8),f'02:{49+k/fps:06.3f}    |    0.25×',font=font,fill='white')
    images.append(im)
images[0].save(p/'Equip_quarter_speed.gif',save_all=True,append_images=images[1:],duration=[130,130,140]*11+[130],loop=0,disposal=2)
