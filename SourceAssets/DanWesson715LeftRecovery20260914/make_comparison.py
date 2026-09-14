"""Arrange the actual model renders into a close/regrip comparison."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parent/'Inspection'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for kind,seconds in [('single_0_6',1.16),('speed_0',1.31*3.85/3.6)]:
    frames=[]
    for i in range(36):
        frame=Image.new('RGB',(1280,476),(27,31,38));d=ImageDraw.Draw(frame)
        d.text((18,8),'BEFORE - left follows gun flick',fill=(239,196,140),font=font)
        d.text((658,8),'AFTER - independent recovery',fill=(151,226,183),font=font)
        for side,mode in enumerate(('before','after')):
            with Image.open(root/(mode+'-motion')/f'{kind}_{i}.png') as render:
                frame.paste(render.convert('RGB'),(side*640,36))
        frames.append(frame)
    duration=[round(seconds*1000/35)]*35+[600]
    frames[0].save(root/(kind+'-comparison.gif'),save_all=True,append_images=frames[1:],duration=duration,loop=0,optimize=True)
print('DW715_CLOSE_COMPARISONS_WRITTEN')
