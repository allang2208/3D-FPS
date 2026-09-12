from pathlib import Path
from PIL import Image
import json,imageio_ffmpeg
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912');count=json.loads((R/'Candidates/CMU02_07/attack-authoring.json').read_text())['frames']//2
frames=[Image.open(R/'Previews/FBX_CMU/Attack'/f'{i:04d}.png').convert('RGB') for i in range(count)]
duration=[(round((i+1)*100/15)-round(i*100/15))*10 for i in range(count)]
frames[0].save(R/'Previews/InfectedMiner_CMU_Attack.gif',save_all=True,append_images=frames[1:],duration=duration,loop=0)
w=imageio_ffmpeg.write_frames(str(R/'Previews/InfectedMiner_CMU_Attack.mp4'),frames[0].size,fps=15,codec='libx264',quality=8,pix_fmt_in='rgb24',pix_fmt_out='yuv420p',macro_block_size=2);w.send(None)
for f in frames:w.send(f.tobytes())
w.close();print('CMU_MINER_PREVIEW_PACKAGED')
