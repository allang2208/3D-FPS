"""Encode the requested meteor preview from real 60 Hz UE capture frames."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

parser=argparse.ArgumentParser()
parser.add_argument('capture',type=Path)
parser.add_argument('--width',type=int,default=960)
args=parser.parse_args()
indices=list(range(0,180,2))
frames=[]
for index in indices:
    with Image.open(args.capture/f'frame-{index:04d}.png') as source:
        frame=source.convert('RGB')
        if args.width!=frame.width:
            frame=frame.resize((args.width,round(frame.height*args.width/frame.width)),Image.Resampling.LANCZOS)
        frames.append(frame)
# A shared palette avoids per-frame palette flicker. No exposure/color grading,
# synthetic interpolation, retouching or changes to the recorded motion.
palette_source=Image.new('RGB',(160*10,90*9))
for index,frame in enumerate(frames):
    palette_source.paste(frame.resize((160,90),Image.Resampling.LANCZOS),((index%10)*160,(index//10)*90))
palette=palette_source.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
encoded=[frame.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG) for frame in frames]
# GIF timing is in 10 ms units: 30+40+30 ms for three 30 Hz frames.
# Using 33 ms for every frame would truncate to 30 and accelerate the effect.
durations=[30,40,30]*(len(encoded)//3)
suffix='' if args.width==960 else f'-{args.width}px'
output=args.capture/f'meteor-fireball-impact-normal{suffix}.gif'
encoded[0].save(output,save_all=True,append_images=encoded[1:],duration=durations,
                loop=0,optimize=False,disposal=2)
sheet=Image.new('RGB',(960,408),'#171b20')
draw=ImageDraw.Draw(sheet)
for slot,index in enumerate((38,43,49,59,77,107)):
    with Image.open(args.capture/f'frame-{index:04d}.png') as source:
        x,y=(slot%3)*320,(slot//3)*204
        sheet.paste(source.convert('RGB').resize((320,180),Image.Resampling.LANCZOS),(x,y+24))
        draw.text((x+8,y+6),f'Impact {(index+1)/60-.65:+.3f}s',fill='white')
sheet.save(args.capture/'gif-contact-sheet.jpg',quality=94)
receipt=dict(source='Current FPSGAME AFPSMeteorStrike offscreen rendering',source_frames=180,
             source_fps=60,gif_frames=len(encoded),gif_duration_seconds=sum(durations)/1000,
             resolution=list(frames[0].size),playback='original speed, looping',
             gif=str(output),effects_modified=False,gameplay_acceptance=False)
(args.capture/f'gif-receipt{suffix}.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt),flush=True)
