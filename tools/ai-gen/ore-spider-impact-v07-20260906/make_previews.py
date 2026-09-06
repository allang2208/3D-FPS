from pathlib import Path
from PIL import Image
p=Path(__file__).resolve().parent
paths=sorted((p/'throw').glob('*.png'));assert len(paths)==82
frames=[Image.open(f).convert('RGB').resize((960,540)) for f in paths]
durations=[round((i+1)*1000/24/10)*10-round(i*1000/24/10)*10 for i in range(82)]
frames[0].save(p/'throw.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0)
print('GIF',len(frames),sum(durations))
