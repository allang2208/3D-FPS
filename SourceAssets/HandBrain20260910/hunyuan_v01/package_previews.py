from pathlib import Path
from PIL import Image,ImageDraw
import imageio_ffmpeg,subprocess,json
root=Path(__file__).resolve().parent;out=root/'delivery'
records={}
for name,count in [('Idle',24),('Move',12),('Attack_Slam',24)]:
    files=sorted((root/'preview_frames'/name).glob('*.png'));assert len(files)==count
    frames=[Image.open(p).convert('RGB') for p in files]
    durations=[80,80,90]*(count//3)
    frames[0].save(out/(name+'.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False)
    writer=imageio_ffmpeg.write_frames(str(out/(name+'.mp4')),size=frames[0].size,fps=12,codec='libx264',pix_fmt_in='rgb24',output_params=['-crf','18'])
    writer.send(None)
    for f in frames:writer.send(f.tobytes())
    writer.close()
    records[name]={'rendered_frames':count,'playback_fps':12,'duration_s':count/12,'gif_repeat_is_preview_only':name=='Attack_Slam'}
frames=[Image.open(root/'preview_frames/Attack_Slam'/f'{i:03}.png').resize((320,320)) for i in [0,5,9,12,16,22]]
sheet=Image.new('RGB',(960,680),'#dddddd');draw=ImageDraw.Draw(sheet)
for j,(f,i) in enumerate(zip(frames,[0,5,9,12,16,22])):
    x=(j%3)*320;y=(j//3)*340;sheet.paste(f,(x,y));draw.text((x+8,y+323),f'Attack {i/12:.2f}s',fill='black')
sheet.save(out/'Attack_contact_sheet.png')
(out/'preview_manifest.json').write_text(json.dumps(records,indent=2))
overview=[]
for k in range(24):
    canvas=Image.new('RGB',(960,344),'#dddddd');draw=ImageDraw.Draw(canvas)
    for j,(name,label,count) in enumerate([('Idle','IDLE | 2s',24),('Move','MOVE | 1s loop',12),('Attack_Slam','ATTACK | impact 1.0s',24)]):
        frame=Image.open(root/'preview_frames'/name/f'{k%count:03}.png').resize((320,320))
        canvas.paste(frame,(j*320,24));draw.text((j*320+12,6),label,fill='black')
    overview.append(canvas)
overview[0].save(out/'ThreeAnimations.gif',save_all=True,append_images=overview[1:],duration=[80,80,90]*8,loop=0,optimize=False)
