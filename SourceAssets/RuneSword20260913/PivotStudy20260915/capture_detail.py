"""Exact-time frame sequences for pivot/contact reasoning, from user reference."""
import json,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
P=Path(__file__).parent
name,start,step,count=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),int(sys.argv[4])
out=P/name;out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
records=[]
for i in range(count):
    t=start+step*i;path=out/f'frame_{i:03d}.png'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-ss',f'{t:.6f}',
                    '-i',str(P/'p1_reference_video_only.mp4'),'-frames:v','1',str(path)],check=True)
    records.append({'seconds':t,'file':path.name})
for first in range(0,count,9):
    sheet=Image.new('RGB',(1440,1194),'#171a20')
    for j,item in enumerate(records[first:first+9]):
        frame=Image.open(out/item['file']).convert('RGB')
        # Native right-hand teaching area; include wrist and first handle section.
        detail=frame.crop((260,125,535,360)).resize((468,360),Image.Resampling.LANCZOS)
        x,y=(j%3)*480,(j//3)*398
        sheet.paste(detail,(x,y));ImageDraw.Draw(sheet).text((x+9,y+364),f'P1 {item["seconds"]:07.3f} s',font=font,fill='white')
    sheet.save(out/f'sheet_{first//9+1:02d}.jpg',quality=95)
(out/'frames.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(name,count,'reference frames',flush=True)
