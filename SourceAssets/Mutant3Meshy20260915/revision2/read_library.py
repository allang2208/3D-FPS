import json,struct,urllib.request,urllib.parse,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT.parents[1]/'FatZombieMeshy20260913/.python-deps'))
import imageio_ffmpeg
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
(ROOT/'reference_videos').mkdir(exist_ok=True)
commit='2d3d1ff03247d9e7e830d1ae375653da4e2146e2'
names=['Jog','Run_Stealth','Zombie_Walk_2','Hit_Chest','Hit_Head','Hit_Knockback']
rows=[]
for name in names:
    video=ROOT/'reference_videos'/(name+'.mp4')
    if not video.exists():
        urllib.request.urlretrieve(f'https://raw.githubusercontent.com/Mesh2Motion/mesh2motion-app/{commit}/static/animpreviews/human/light_{urllib.parse.quote(name)}.mp4',video)
    reader=imageio_ffmpeg.read_frames(str(video)); info=next(reader); reader.close()
    row=Image.new('RGB',(1200,245),'#ddd'); draw=ImageDraw.Draw(row)
    for i,fraction in enumerate([0,.2,.4,.6,.85]):
        out=ROOT/'reference_videos'/f'{name}_{i}.png'
        subprocess.run([ffmpeg,'-y','-loglevel','error','-ss',str(info['duration']*fraction),'-i',str(video),'-frames:v','1',str(out)],check=True)
        im=Image.open(out).convert('RGB'); im=im.resize((180,216))
        row.paste(im,(i*240+30,25)); draw.text((i*240+4,4),f'{name} {info["duration"]*fraction:.2f}s',fill='black')
    rows.append(row)
sheet=Image.new('RGB',(1200,245*len(rows)),'white')
for i,row in enumerate(rows): sheet.paste(row,(0,i*245))
sheet.save(ROOT/'library_reference.jpg')
print('SOURCE_ANIMATION_REFERENCES_READY')
