"""Deliver the saved pose readback at the original 60 Hz, with a lightweight GIF."""
from pathlib import Path
import json, subprocess
import imageio_ffmpeg
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'Review/VideoFitV3'
encoder=imageio_ffmpeg.get_ffmpeg_exe()
for case in ['StandardIdleEntry','Standard','LongGripIdleEntry','LongGrip']:
    source=ROOT/case/'MotionPreview'
    native=json.loads((source.parent/'surface.json').read_text(encoding='utf-8-sig'))
    paths=[source/f'f{index:04d}.png' for index in range(0,len(native['frames']),2)]
    frames=[Image.open(path).convert('RGB') for path in paths]
    width,height=frames[0].size
    output=HERE/f'HighlandSweep_V3_{case}.mp4'
    # yuv420p requires even dimensions. Preserve aspect and pad one bottom row.
    command=[encoder,'-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r','60','-i','-','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-an','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    result=subprocess.run(command,input=b''.join(frame.tobytes() for frame in frames));result.check_returncode()
    if case=='StandardIdleEntry':
        gif=frames[::2];delay=[10*(round((i+1)*100/30)-round(i*100/30)) for i in range(len(gif))];delay[-1]=350
        gif[0].save(HERE/'HighlandSweep_V3.gif',save_all=True,append_images=gif[1:],duration=delay,optimize=False,loop=0)
