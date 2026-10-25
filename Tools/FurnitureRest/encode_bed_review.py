"""Create bed-family GIFs and the six-family saved-pose overview."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8/ReviewSaved')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
labels={'Bed':'普通床','BedKing':'加大双人床','ApartmentBed':'公寓加宽床','Bunk':'下铺','Hospital':'普通病床','Ward':'高位病床'}
phases={'Enter':'上床躺下','Idle':'躺稳','Exit':'起身下床'}
frames={k:sorted((ROOT/'frames'/k).glob('*.png')) for k in labels}
times={k:json.loads((ROOT/(k+'_timeline.json')).read_text()) for k in labels}
def save_gif(path,sequence):
    palette=sequence[len(sequence)//2].quantize(colors=192)
    q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in sequence]
    q[0].save(path,save_all=True,append_images=q[1:],duration=[80 if i%3!=2 else 90 for i in range(len(q))],loop=0,disposal=2,optimize=True)
for filename,pair in [('bed_and_bunk.gif',('Bed','Bunk')),('apartment_and_hospital.gif',('ApartmentBed','Hospital'))]:
    sequence=[]
    for i in range(max(len(frames[k]) for k in pair)):
        im=Image.new('RGB',(1200,650),(29,35,42));draw=ImageDraw.Draw(im)
        for col,k in enumerate(pair):
            j=min(i,len(frames[k])-1);im.paste(Image.open(frames[k][j]).convert('RGB'),(col*600,42))
            draw.text((col*600+16,7),labels[k]+' · '+phases[times[k][j][0]],font=font,fill=(239,243,248))
        draw.text((16,625),'实际保存动作 · 中性材质离线预览',font=small,fill=(204,211,222))
        sequence.append(im.resize((1000,542),Image.Resampling.LANCZOS))
    save_gif(ROOT/filename,sequence);print('BED_REVIEW_GIF',filename,flush=True)
sheet=Image.new('RGB',(1200,870),(29,35,42));draw=ImageDraw.Draw(sheet)
for i,k in enumerate(labels):
    row,col=divmod(i,3);j=next(j for j,(phase,t) in enumerate(times[k]) if phase=='Idle')
    sheet.paste(Image.open(frames[k][j]).convert('RGB').resize((400,400)),(col*400,row*435+35))
    draw.text((col*400+10,row*435+5),labels[k],font=font,fill=(239,243,248))
sheet.save(ROOT/'six_bed_types.jpg',quality=94)
# Use complete entry, settled and exit samples for the final visual review.
contact=Image.new('RGB',(1800,1800),(29,35,42));draw=ImageDraw.Draw(contact)
for row,k in enumerate(labels):
    e=[i for i,(p,t) in enumerate(times[k]) if p=='Enter'];x=[i for i,(p,t) in enumerate(times[k]) if p=='Exit']
    chosen=[e[0],e[len(e)//3],e[2*len(e)//3],next(i for i,(p,t) in enumerate(times[k]) if p=='Idle'),x[len(x)//2],x[-1]]
    for col,j in enumerate(chosen):
        contact.paste(Image.open(frames[k][j]).convert('RGB').resize((300,270)),(col*300,row*300+30))
        draw.text((col*300+6,row*300+3),labels[k]+' '+phases[times[k][j][0]],font=small,fill=(239,243,248))
contact.save(ROOT/'bed_transition_sheet.jpg',quality=94)
