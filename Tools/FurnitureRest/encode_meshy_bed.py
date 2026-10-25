"""Make the ordinary-bed GIF from saved compressed animations and real geometry."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','MeshyBed20261024')
preview=OUT/'ReviewSaved'
KIND=globals().get('FURNITURE_KIND','Bed')
timeline=json.loads((preview/(KIND+'_timeline.json')).read_text())
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
labels={'Enter':'入座 → 双手支撑 → 抬腿躺下','Idle':'休息','Exit':'起身下床'}
frames=[]
for i,(phase,t) in enumerate(timeline):
    im=Image.new('RGB',(600,655),(29,35,42));draw=ImageDraw.Draw(im)
    im.paste(Image.open(preview/'frames'/KIND/f'{i:04d}.png').convert('RGB'),(0,30))
    draw.text((12,3),labels[phase]+f'  {t:.1f}s',font=font,fill='white')
    draw.text((12,633),'UE 已保存动作 · 项目角色与床模型 · 离线预览',font=small,fill=(204,211,222))
    frames.append(im)
palette=frames[len(frames)//3].quantize(colors=192)
encoded=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
entry_end_phase='Exit' if globals().get('ENTRY_INCLUDE_IDLE',True) else 'Idle'
for filename,end in [('bed_full_cycle.gif',len(frames)),('bed_entry.gif',next(i for i,(p,t) in enumerate(timeline) if p==entry_end_phase))]:
    encoded[0].save(preview/filename,save_all=True,append_images=encoded[1:end],
                    duration=[90 if i%3==2 else 80 for i in range(end)],loop=0,disposal=2,optimize=True)
sheet=Image.new('RGB',(1200,900),(29,35,42))
times=(.4,.8,1.5,2.8,3.5,4.3,5.,5.7,6.5,7.3,8.,8.85) if KIND=='Bed' else (.4,1.2,2.2,3.2,4.5,5.3,6.4,7.,8.,9.,10.,10.95)
times=globals().get('POSE_TIMES',times)
for j,t in enumerate(times):
    index=min(range(len(timeline)),key=lambda i:abs(timeline[i][1]-t) if timeline[i][0]=='Enter' else 1e9)
    im=Image.open(preview/'frames'/KIND/f'{index:04d}.png').convert('RGB').resize((300,300),Image.Resampling.LANCZOS)
    sheet.paste(im,((j%4)*300,(j//4)*300));ImageDraw.Draw(sheet).text(((j%4)*300+8,(j//4)*300+5),f'{t:.2f}s',font=small,fill='white')
sheet.save(preview/'bed_entry_sheet.jpg',quality=94)
print('MESHY_BED_GIFS',preview/'bed_entry.gif',preview/'bed_full_cycle.gif')
