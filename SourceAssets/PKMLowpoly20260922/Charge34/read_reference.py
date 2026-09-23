from pathlib import Path
import subprocess
from PIL import Image, ImageDraw

O=Path(__file__).parent; R=O.parent
ffmpeg=R.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
frames=O/'ReferenceFrames';frames.mkdir(parents=True,exist_ok=True)
subprocess.run([str(ffmpeg),'-v','error','-y','-ss','24.0','-i',str(R/'References/PKM_UserReloadReference.mp4'),
    '-t','1.44','-vf','fps=16.6666667','-q:v','3',str(frames/'charge_%02d.jpg')],check=True)
sheet=Image.new('RGB',(1600,6*255),'#202328');draw=ImageDraw.Draw(sheet)
for i,path in enumerate(sorted(frames.glob('charge_*.jpg'))):
    im=Image.open(path);w,h=im.size
    crop=im.crop((int(w*.47),int(h*.38),w,int(h*.94)))
    crop.thumbnail((396,229))
    x,y=i%4*400,i//4*255;sheet.paste(crop,(x,y))
    draw.text((x+8,y+233),f'{24+i*.06:.2f}s',fill='white')
sheet.save(O/'charge_direction_reference.jpg',quality=82)
print('Saved charge direction reference')
