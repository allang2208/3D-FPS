from pathlib import Path
import cv2
from PIL import Image,ImageDraw
O=Path(__file__).parent;cap=cv2.VideoCapture(str(O/'reference_video.m4s'))
times=[40.5+i*.5 for i in range(20)];w,h=426,266;sheet=Image.new('RGB',(w*4,h*5),(25,25,25));d=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read()
    if not ok:raise RuntimeError(t)
    im=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));im.thumbnail((w,240));x=i%4*w;y=i//4*h;sheet.paste(im,(x,y+24));d.text((x+8,y+5),f'{t:.2f} s',fill='white')
sheet.save(O/'40.5-50_motion_sheet.jpg',quality=94)
