from pathlib import Path
from PIL import Image, ImageDraw
import imageio_ffmpeg, json
root=Path(__file__).resolve().parent
source=Path('Y:/开发/游戏/素材库/怪物/手脑')
metadata={}
for n,path in enumerate(sorted(source.glob('*.mp4'))):
    stream=imageio_ffmpeg.read_frames(str(path))
    meta=next(stream);metadata[path.name]=meta
    indices=[round(i*meta['fps']*(meta['duration']-.15)/7) for i in range(8)]
    sheet=Image.new('RGB',(1280,680),'#dddddd');draw=ImageDraw.Draw(sheet)
    for i,data in enumerate(stream):
        if i not in indices:continue
        j=indices.index(i)
        frame=Image.frombytes('RGB',meta['size'],data).resize((320,320))
        x=(j%4)*320;y=(j//4)*340
        sheet.paste(frame,(x,y));draw.text((x+8,y+321),f'{i/meta["fps"]:.2f}s',fill='black')
    sheet.save(root/f'source_video_{n}_contact.png')
(root/'source_video_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
