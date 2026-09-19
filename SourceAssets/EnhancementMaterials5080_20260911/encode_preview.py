import subprocess
from pathlib import Path
import imageio_ffmpeg
P=Path(__file__).parent
assert len(list((P/'turntable_frames').glob('frame_*.png')))==36
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','8','-i',str(P/'turntable_frames/frame_%04d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(P/'Delivery/turntable.mp4')],check=True)
