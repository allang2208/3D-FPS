"""Package native Blender render frames at the authored playback speed."""
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/ArmContinuityV16/Inspection')
frames=[]
for file in sorted((ROOT/'Frames').glob('claw_*.png')):
    frame=Image.open(file).convert('RGB');draw=ImageDraw.Draw(frame)
    draw.rectangle((0,0,640,28),fill=(24,29,34))
    draw.text((12,8),'M09 V16 | continuous arms | offline geometry preview',fill=(232,237,242))
    frames.append(frame)
if len(frames)!=34:raise RuntimeError('Incomplete authored preview frames')
frames[0].save(ROOT/'M09_Claw_Continuous_V16.gif',save_all=True,append_images=frames[1:],
    duration=[33]*33+[500],loop=0,optimize=False,disposal=2)
print('M09_CLAW_PREVIEW_GIF_SAVED')
