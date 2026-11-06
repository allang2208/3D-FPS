from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import cv2,sys
p=Path(__file__).resolve().parent;case=sys.argv[1] if len(sys.argv)>1 else 'StandardIdleEntry'; images=p.parent/'Review/VideoFitV3'/case/'MotionPreview';c=cv2.VideoCapture(str(p.parent/'ReferenceV2/kubold-indexed.mp4'));ids=[1034,1048,1053,1056,1059,1063,1068,1075,1082,1089,1095,1102,1108,1114]; w,h=304,171;s=Image.new('RGB',(4*w,((len(ids)+1)//2)*(h+18)),'#172331');draw=ImageDraw.Draw(s)
for j,i in enumerate(ids):
 c.set(1,i);ok,f=c.read();a=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB)).resize((w,h));b=Image.open(images/f'f{2*(i-1034):04}.png').resize((w,h));x=(j%2)*2*w;y=(j//2)*(h+18);s.paste(a,(x,y));s.paste(b,(x+w,y));draw.text((x+5,y+h),f'ref {i} | {i/60:.3f} s');draw.text((x+w+5,y+h),case)
s.save(p/('compare-'+case+'.jpg'),quality=87)
