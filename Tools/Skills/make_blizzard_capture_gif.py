"""Encode real UE Blizzard frames without changing their color or motion."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

parser=argparse.ArgumentParser()
parser.add_argument('capture',type=Path)
args=parser.parse_args()
paths=sorted(args.capture.glob('frame-*.png'))
if not paths:
    raise RuntimeError('No recorded Blizzard frames')
frames=[]
for path in paths:
    with Image.open(path) as source:
        frames.append(source.convert('RGB'))
palette_source=Image.new('RGB',(160*12,90*math.ceil(len(frames)/12)))
for i,frame in enumerate(frames):
    palette_source.paste(frame.resize((160,90),Image.Resampling.LANCZOS),((i%12)*160,(i//12)*90))
palette=palette_source.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
encoded=[frame.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG) for frame in frames]
output=args.capture/'blizzard-cloud-cold-mist.gif'
encoded[0].save(output,save_all=True,append_images=encoded[1:],duration=50,loop=0,optimize=False,disposal=2)
sheet=Image.new('RGB',(960,588),'#171b20')
draw=ImageDraw.Draw(sheet)
for slot,index in enumerate((15,35,60,min(95,len(frames)-1))):
    x,y=(slot%2)*480,(slot//2)*294
    sheet.paste(frames[index].resize((480,270),Image.Resampling.LANCZOS),(x,y+24))
    draw.text((x+8,y+6),f'Blizzard  {index/20:.2f} s',fill='white')
sheet.save(args.capture/'keyframes.jpg',quality=95)
receipt={'source':'FPSGAME AFPSBlizzardZone offscreen render','fixture':'flat floor, no weather, level-one footprint',
         'gif_frames':len(frames),'fps':20,'duration_seconds':len(frames)/20,'resolution':list(frames[0].size),
         'playback':'original speed, looping','gif':str(output),'assets_modified':False,'retouched':False}
(args.capture/'gif-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt),flush=True)
