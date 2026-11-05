"""Combine the saved-action views into half-speed, looping review clips."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out=Path(__file__).resolve().parent/'GIF'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
for family,label in [('skeleton_base','默认握把 · 5 发'),('skeleton_mag10_balanced','平衡握把 · 10 发'),('skeleton_mag10_stable','防滑握把 · 10 发')]:
    frames=[]
    for i in range(28):
        frame=Image.new('RGB',(960,345),(27,32,38))
        draw=ImageDraw.Draw(frame)
        for side,(view,title) in enumerate([('fps','第一人称'),('grip','右手近景')]):
            with Image.open(out/family/f'{i:03d}_{view}.png') as source:
                frame.paste(source.convert('RGB').resize((480,315),Image.Resampling.LANCZOS),(480*side,30))
            draw.text((480*side+8,2),f'{label} | {title}' if side==0 else f'{title} | {i/30:.2f} 秒',font=font,fill='white')
        frames.append(frame)
    durations=[round((i+1)*20/3)*10-round(i*20/3)*10 for i in range(28)]
    durations[-1]=320
    frames[0].save(out/f'M24_R3_{family}.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=1,optimize=False)
