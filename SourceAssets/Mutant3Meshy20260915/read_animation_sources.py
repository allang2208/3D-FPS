import sys, urllib.request, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT.parent/'FatZombieMeshy20260913/.python-deps'))
import imageio_ffmpeg
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
folder=ROOT/'sources/reference_videos';folder.mkdir(exist_ok=True)
commit='2d3d1ff03247d9e7e830d1ae375653da4e2146e2'
names=['Zombie_Idle_Crouch','Zombie_Scratch']
rows=[]
for name,seconds in zip(names,[2.9167,1.79167]):
    path=folder/(name+'.mp4')
    if not path.exists():
        urllib.request.urlretrieve(f'https://raw.githubusercontent.com/Mesh2Motion/mesh2motion-app/{commit}/static/animpreviews/human/light_{name}.mp4',path)
    reader=imageio_ffmpeg.read_frames(str(path))
    video_meta=next(reader);reader.close()
    seconds=float(video_meta['duration'])
    print(name,video_meta,flush=True)
    row=Image.new('RGB',(1200,270),'#dddddd');draw=ImageDraw.Draw(row)
    for idx,fraction in enumerate([0,.20,.40,.60,.85]):
        frame=folder/f'{name}_{idx}.png'
        subprocess.run([ffmpeg,'-y','-loglevel','error','-ss',str(seconds*fraction),'-i',str(path),'-frames:v','1',str(frame)],check=True)
        im=Image.open(frame).convert('RGB');im.thumbnail((240,240))
        row.paste(im,(idx*240+(240-im.width)//2,25));draw.text((idx*240+4,4),f'{name} {seconds*fraction:.2f}s',fill='black')
    rows.append(row)
sheet=Image.new('RGB',(1200,540),'white')
for i,row in enumerate(rows):sheet.paste(row,(0,i*270))
sheet.save(folder/'source_reference_frames.jpg')
print(folder/'source_reference_frames.jpg')

