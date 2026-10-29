"""Package requested review GIFs and readable contact sheets."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
info=json.loads((OUT/'gif-preview.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
sheet_indices=[0,8,15,20,26,32,39,47,52,57,61,63]
for label in ('jason','kaitlin'):
    frames=[]
    for k,t in enumerate(info['times']):
        canvas=Image.new('RGB',(1040,664),(20,25,32));d=ImageDraw.Draw(canvas)
        stage='WINDUP' if t<.5 else 'SPIN' if t<1.566667 else 'RECOVERY'
        d.text((16,8),f'{label.title()} / V11 / {stage} / {t:.3f}s',font=font,fill='white')
        d.text((16,36),'Fixed camera / gameplay rotation',font=small,fill=(172,206,231))
        d.text((536,36),'Heading locked / joint detail',font=small,fill=(172,206,231))
        for i,view in enumerate(('world','locked')):
            canvas.paste(Image.open(OUT/'GifFrames'/f'{label}_{view}_{k:03d}.png'),(i*520,64))
        frames.append(canvas)
    # One palette avoids frame-to-frame color shimmer and keeps the GIF small.
    palette_source=Image.new('RGB',(8*104,8*66))
    for k,frame in enumerate(frames):
        palette_source.paste(frame.resize((104,66)),((k%8)*104,(k//8)*66))
    palette=palette_source.quantize(colors=96)
    gif_frames=[frame.resize((832,531),Image.Resampling.LANCZOS).quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    for speed,mult in [('normal',1),('slow',2)]:
        durations=[(30 if k%3!=2 else 40)*mult for k in range(len(frames))]
        durations[0]=350;durations[-1]=650
        path=OUT/f'{label}-V11-{speed}.gif'
        gif_frames[0].save(path,save_all=True,append_images=gif_frames[1:],duration=durations,loop=0,optimize=True,disposal=2)
    indices=[min(i,len(frames)-1) for i in sheet_indices]
    sheet=Image.new('RGB',(1300,4*332),(20,25,32));d=ImageDraw.Draw(sheet)
    for j,k in enumerate(indices):
        im=Image.open(OUT/'GifFrames'/f'{label}_locked_{k:03d}.png').resize((325,300))
        x=(j%4)*325;y=(j//4)*332
        sheet.paste(im,(x,y+32));d.text((x+8,y+7),f'{info["times"][k]:.3f}s',font=small,fill='white')
    sheet=sheet.crop((0,0,1300,996));sheet.save(OUT/f'{label}-V11-contact.jpg',quality=91)
    sheet=Image.new('RGB',(1300,1328),(20,25,32));d=ImageDraw.Draw(sheet)
    for j,k in enumerate((0,8,15,18,21,24,27,30,33,36,39,42,47,52,57,63)):
        im=Image.open(OUT/'GifFrames'/f'{label}_world_{k:03d}.png').resize((325,300))
        x=(j%4)*325;y=(j//4)*332
        sheet.paste(im,(x,y+32));d.text((x+8,y+7),f'{info["times"][k]:.3f}s',font=small,fill='white')
    sheet.save(OUT/f'{label}-V11-world-contact.jpg',quality=91)
    sheet=Image.new('RGB',(1560,664),(20,25,32));d=ImageDraw.Draw(sheet)
    for row,side in enumerate(('r','l')):
        for j,k in enumerate((8,15,26,47,52,57)):
            im=Image.open(OUT/'GifFrames'/f'{label}_hand_{side}_{k:03d}.png').resize((260,300))
            x=j*260;y=row*332;sheet.paste(im,(x,y+32))
            d.text((x+8,y+7),f'{side.upper()} / {info["times"][k]:.3f}s',font=small,fill='white')
    sheet.save(OUT/f'{label}-V11-hands.jpg',quality=94)
print('V11_GIFS_COMPLETE')
