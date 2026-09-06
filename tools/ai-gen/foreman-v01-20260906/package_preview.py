from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
for clip,duration in [('Idle',1),('Walk',1.5),('Attack',1.5),('Howl',3),('Death',1.4)]:
 paths=sorted((ROOT/'runtime'/clip).glob('*.png'))
 expected=int(__import__('math').ceil(duration*24))+1
 if len(paths)!=expected:raise RuntimeError(f'{clip}: {len(paths)}/{expected} rendered frames')
 frames=[]
 for path in paths:
  im=Image.open(path).convert('RGB');im.thumbnail((640,480));frames.append(im)
 # GIF delays use 10ms units; preserve total duration after quantization.
 if clip!='Death':frames=frames[:-1]
 count=len(frames)-1 if clip=='Death' else len(frames)
 times=[round((i+1)*duration*100/count)*10-round(i*duration*100/count)*10 for i in range(count)]
 if clip=='Death':times.append(1000)
 frames[0].save(ROOT/(clip+'.gif'),save_all=True,append_images=frames[1:],duration=times,loop=0,disposal=2)
 print(clip,len(frames),sum(times))
