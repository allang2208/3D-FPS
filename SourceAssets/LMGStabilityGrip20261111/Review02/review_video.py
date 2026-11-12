"""Review film from real player viewport and time-matched wrist captures."""
from bisect import bisect_left
from pathlib import Path
from functools import lru_cache
import json, sys, subprocess
import imageio_ffmpeg
import numpy as np
from PIL import Image,ImageDraw,ImageFont
run=Path(sys.argv[1])
visual=run/'host/Visual'
def rows(kind):
    return [json.loads(s) for s in (visual/(kind+'.jsonl')).read_text().splitlines()]
def nearest(seq,t):
    j=bisect_left([r['time'] for r in seq],t)
    return min(seq[max(j-1,0):min(j+1,len(seq))],key=lambda x:abs(x['time']-t))
@lru_cache(maxsize=50)
def frame(path,size):
    with Image.open(path) as im:
        return im.convert('RGB').resize(size,Image.Resampling.BILINEAR)
owners=rows('owner')
close=rows('close')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
names=['M249 无握把','M249 稳固握把','201 稳固握把','PKM 稳固握把']
phases=['','待机','瞄准','换弹','回握','再次瞄准','待机']
args=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1088x464','-r','12','-i','-','-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(run/'grip-review.mp4')]
with subprocess.Popen(args,stdin=subprocess.PIPE) as movie:
    for case in range(8):
        seq=[r for r in owners if r['case']==case and (visual/'Owner'/r['image']).exists()]
        sides=[[r for r in close if r['case']==case and Path(r['image']).stem.endswith('_'+str(i))] for i in range(2)]
        # Start at the settled idle, run across ADS and the full mechanical action
        # at wall-clock speed. Include the second ADS and return to idle.
        start=next((r['time'] for r in seq if r['stage']==1 and r['stage_time']>=2.7),seq[0]['time'])
        for t in np.arange(start,seq[-1]['time']+.001,1/12):
            owner=nearest(seq,t)
            canvas=Image.new('RGB',(1088,464),'#1c2026')
            draw=ImageDraw.Draw(canvas)
            draw.text((8,5),names[case//2]+'   ·   '+('空仓换弹' if case%2 else '普通换弹')+'   ·   '+phases[owner['stage']],font=font,fill='white')
            canvas.paste(frame(visual/'Owner'/owner['image'],(608,342)),(0,72))
            draw.text((4,423),'第一人称实拍',font=font,fill='white')
            for i,side in enumerate(sides):
                sample=nearest(side,t)
                canvas.paste(frame(visual/'Close'/sample['image'],(238,238)),(610+239*i,100))
                draw.text((615+239*i,352),'掌侧近景' if i==0 else '指侧近景',font=font,fill='white')
            movie.stdin.write(canvas.tobytes())
    movie.stdin.close()
    if movie.wait()!=0: raise RuntimeError('video encoding failed')
