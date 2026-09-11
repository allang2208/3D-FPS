from pathlib import Path
from PIL import Image
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/sculpt_v06')
frames=[Image.open(p).convert('RGB') for p in sorted((r/'preview_frames').glob('*.png'))]
assert len(frames)==23
# GIF time resolution is 10 ms; alternate 130/140 ms to total 3 seconds.
durations=[130]*22+[140]
frames[0].save(r/'Howl_Sculpt.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0)
print('SCULPT_PREVIEW_PACKAGED')
