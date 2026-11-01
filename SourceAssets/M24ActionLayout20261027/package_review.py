import json,sys,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;P=O.parents[1];D=O/sys.argv[1]
data=json.loads((D/'runtime.json').read_text(encoding='utf-8-sig'))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
rows=data['frames'];groups={}
for row in rows:groups.setdefault(row['phase'],[]).append(row)
stats={};out=D/'Sheets';out.mkdir(exist_ok=True)
for phase,items in groups.items():
    valid=[r for r in items if (D/'Frames'/r['image']).exists()]
    stats[phase]={'samples':len(items),'screenshots':len(valid),'duration':max(r['phase_time'] for r in items),
      'max_action_framing':max(r['action_framing'] for r in items),
      'clips':sorted(set(r['clip'] for r in items)),
      'max_source_time':max(r['source_time'] for r in items)}
    picks=[valid[round(i*(len(valid)-1)/11)] for i in range(12)]
    sheet=Image.new('RGB',(1280,4*204),(29,32,38));draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(picks):
        im=Image.open(D/'Frames'/r['image']).convert('RGB');im.thumbnail((320,180))
        x=(i%4)*320;y=(i//4)*204
        sheet.paste(im,(x,y));draw.text((x+4,y+181),f"{phase} {r['phase_time']:.2f}s / src {r['source_time']:.2f}",font=font,fill=(235,235,235))
    sheet=sheet.crop((0,0,1280,612));sheet.save(out/(phase+'.jpg'),quality=90)
    # Preserve every recorded frame for review; the twelve-frame sheets are only an index.
    for start in range(0,len(valid),96):
        page=valid[start:start+96];cols=8;cellw=192;cellh=130
        contact=Image.new('RGB',(cols*cellw,((len(page)+cols-1)//cols)*cellh),(29,32,38));d=ImageDraw.Draw(contact)
        for i,r in enumerate(page):
            im=Image.open(D/'Frames'/r['image']).convert('RGB');im.thumbnail((192,108))
            x=(i%cols)*cellw;y=(i//cols)*cellh;contact.paste(im,(x,y))
            d.text((x+2,y+109),f"{r['phase_time']:.2f}s",font=font,fill='white')
        contact.save(out/f'{phase}_all_{start//96+1}.jpg',quality=92)
ff=P/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
size=Image.open(D/'Frames'/rows[0]['image']).size
proc=subprocess.Popen([str(ff),'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{size[0]}x{size[1]}','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(D/'M24_full_actions.mp4')],stdin=subprocess.PIPE)
missing=[]
for r in rows:
    file=D/'Frames'/r['image']
    if not file.exists():missing.append(r['image']);continue
    im=Image.open(file).convert('RGB');draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,size[0],27),fill=(22,25,30));draw.text((10,4),f"M24 | {r['phase']} | {r['phase_time']:.2f}s | runtime camera / 30 fps | silent",font=font,fill='white')
    proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
(D/'summary.json').write_text(json.dumps({'phases':stats,'missing_screenshots':missing,'resolution':size,'video':'M24_full_actions.mp4','runtime':True,'audio_reviewed':False},indent=2),encoding='utf-8')
print('M24_REVIEW_PACKAGED',len(rows),len(groups),'missing',len(missing))
