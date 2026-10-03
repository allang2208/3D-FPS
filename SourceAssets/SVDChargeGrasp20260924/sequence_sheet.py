from PIL import Image,ImageDraw
from pathlib import Path
O=Path(__file__).parent/'Review';files=sorted((O/'Sequence').glob('frame_*.png'))
images=[Image.open(f).convert('RGB') for f in files]
images[0].save(O/'SVD_grasp_source.gif',save_all=True,append_images=images[1:],duration=[30,30,40]*(len(images)//3)+[30]*(len(images)%3),loop=0,optimize=True)
chosen=list(range(0,len(files),3));w,h=480,292;sheet=Image.new('RGB',(w*3,h*((len(chosen)+2)//3)),(22,26,32));draw=ImageDraw.Draw(sheet)
for j,i in enumerate(chosen):
 im=images[i].copy();im.thumbnail((w,h-22));x=j%3*w;y=j//3*h;sheet.paste(im,(x,y+22));draw.text((x+6,y+4),files[i].stem,fill='white')
sheet.save(O/'continuous_sheet.jpg',quality=83)
