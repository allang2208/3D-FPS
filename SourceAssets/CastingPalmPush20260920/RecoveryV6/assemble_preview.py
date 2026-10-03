"""Assemble already rendered source frames; does not capture or run the game."""
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).parent/'Review'
files=sorted((root/'Motion').glob('*.png'))
frames=[Image.open(p).convert('RGB') for p in files]
frames[0].save(root/'casting-recovery.gif',save_all=True,append_images=frames[1:],
    duration=[180]+[50]*(len(frames)-2)+[450],loop=0,optimize=True)
times=[.75,.90,1.,1.10,1.20,1.30,1.40]
board=Image.new('RGB',(360*len(times),302),(39,43,49))
for col,t in enumerate(times):
    im=frames[min(round(t*20),len(frames)-1)].resize((360,278),Image.Resampling.LANCZOS)
    board.paste(im,(360*col,24))
    ImageDraw.Draw(board).text((360*col+10,7),f'{t:.2f} s',fill=(240,240,240))
board.save(root/'recovery-sequence.jpg',quality=88)
print(root/'casting-recovery.gif')
