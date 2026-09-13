"""Package the requested front/side animation preview at original playback speed."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913/Previews')
pickaxe='--pickaxe' in sys.argv
if pickaxe:ROOT=ROOT.parent/'PickaxeSingleHand/Previews'
source=ROOT/('SingleHandPickaxe' if pickaxe else 'DefaultAxe')
metadata=json.loads((source/'render.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
frames=[]
width,height=metadata['size_per_view']
count=len(metadata['source_frames_1_based'])
for i,source_frame in enumerate(metadata['source_frames_1_based']):
    canvas=Image.new('RGB',(width*2,height+66),(14,18,25))
    for j,view in enumerate(['front','side']):
        with Image.open(source/view/f'{i:04d}.png') as picture:canvas.paste(picture.convert('RGB'),(j*width,34))
    draw=ImageDraw.Draw(canvas)
    draw.text((18,7),'FRONT 3/4',font=font,fill=(231,235,243))
    draw.text((width+18,7),'SIDE',font=font,fill=(231,235,243))
    label=f'Pickaxe mining source | Single-hand composite | {metadata["baked_speed"]:.2f}x speed' if pickaxe else 'Original EBS tool motion | 1x speed | Current miner mesh'
    draw.text((18,height+42),label,font=small,fill=(193,201,216))
    draw.text((width*2-185,height+42),f'{(source_frame-1)/30:.2f}s / {metadata["seconds"]:.2f}s',font=small,fill=(193,201,216))
    frames.append(canvas)
# Preserve the baked animation duration in GIF's 10 ms timing units.
times=[(f-1)/30 for f in metadata['source_frames_1_based']]+[metadata['seconds']]
durations=[round(times[i+1]*100)*10-round(times[i]*100)*10 for i in range(count)]
gif=ROOT/('InfectedMiner_SingleHand_Pickaxe_Attack.gif' if pickaxe else 'InfectedMiner_Default_Axe_Attack.gif')
frames[0].save(gif,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False,disposal=2)
mp4=gif.with_suffix('.mp4')
writer=imageio_ffmpeg.write_frames(str(mp4),frames[0].size,fps=count/metadata['seconds'],codec='libx264',quality=8,pix_fmt_in='rgb24',pix_fmt_out='yuv420p',macro_block_size=2)
writer.send(None)
for frame in frames:writer.send(frame.tobytes())
writer.close()
metadata.update({'gif':str(gif),'mp4':str(mp4),'gif_durations_ms':durations,'gif_total_ms':sum(durations),'rendered_frames':count})
(ROOT/'preview.json').write_text(json.dumps(metadata,indent=2))
print('MINER_DEFAULT_GIF_READY '+str(gif))
