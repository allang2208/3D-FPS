"""Silent native UE playback of the four reviewed side-magazine reloads."""
from pathlib import Path
import json, subprocess, sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
r=Path(__file__).resolve().parent
label=sys.argv[1] if len(sys.argv)>1 else 'saved'
root=r/label;out=r/'Preview';out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
file=out/'M249_return_checked.mp4'
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r','20','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(file)]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
cases=[]
for mag in ['30','45']:
    for empty in [False,True]:
        name=f'{mag}_{"empty" if empty else "normal"}_base_player'
        folder=root/name;j=json.loads((folder/'review.json').read_text())
        for row in j['frames']:
            im=Image.open(folder/row['file']).convert('RGB');draw=ImageDraw.Draw(im)
            draw.rectangle((0,0,960,62),fill=(18,23,30))
            draw.text((14,7),f'M249 {mag} 发侧弹匣 · {"空仓换弹" if empty else "普通换弹"}',font=font,fill=(235,238,242))
            draw.text((14,36),f'UE 后台实际动画 · {row["runtime"]:.2f} / {j["duration"]:.1f} 秒 · 静音',font=small,fill=(166,179,194))
            p.stdin.write(np.asarray(im).tobytes())
        cases.append(dict(case=name,duration=j['duration'],frames=len(j['frames'])))
p.stdin.close()
if p.wait():raise RuntimeError('Video encoding failed')
(out/'manifest.json').write_text(json.dumps(dict(source=label+' native UE runtime layers',fps=20,audio=False,cases=cases),indent=2))
print(file)
