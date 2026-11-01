from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent;frames=[]
for f in range(0,56,2):
 canvas=Image.new('RGB',(1280,390),(27,31,38))
 for x,name in [(0,'camera'),(640,'side')]:canvas.paste(Image.open(O/'Playback'/f'{name}_{f:03d}.png'),(x,30))
 d=ImageDraw.Draw(canvas);d.text((12,8),'M24 bolt rematch | Blender source preview | 30 Hz source, shown at 15 fps',fill=(235,235,235));d.text((1100,8),f'{f/30:.2f}s',fill=(235,235,235))
 frames.append(canvas)
frames[0].save(O/'M24_BoltRematch_Source.gif',save_all=True,append_images=frames[1:],duration=[67,66,67]*9+[67],loop=0,optimize=True)
