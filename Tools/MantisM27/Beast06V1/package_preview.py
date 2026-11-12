from PIL import Image,ImageDraw
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates')
roles=['LeftSlash','RightSlash','HitF','HitB','HitL','HitR','Idle']
out=Image.new('RGB',(1200,7*220),(24,25,28)); d=ImageDraw.Draw(out)
for j,role in enumerate(roles):
    for k,i in enumerate([0,3,6,8,12,18] if role!='Idle' else [0,6,12,20,28,39]):
        out.paste(Image.open(p/f'{role}_{i:03d}.png').convert('RGB').resize((200,200)),(k*200,j*220))
        frame=i*2+1 if role!='Idle' else i*10+1
        d.text((k*200+3,j*220+201),f'{role} {((frame-1)/60):.2f}s',fill='white')
    ims=[Image.open(f).convert('RGB') for f in sorted(p.glob(role+'_*.png'))]
    ims[0].save(p/f'{role}.gif',save_all=True,append_images=ims[1:],duration=167 if role=='Idle' else 33,loop=0)
out.save(p/'candidate_contact_sheet.jpg')
pair=[]
for i in range(20):
    frame=Image.new('RGB',(960,508),(24,25,28)); label=ImageDraw.Draw(frame)
    for j,role in enumerate(['LeftSlash','RightSlash']):
        frame.paste(Image.open(p/f'{role}_{i:03d}.png').convert('RGB'),(480*j,28))
        label.text((480*j+12,8),f'{role} / Beast06V1 / {i/30:.2f}s',fill='white')
    pair.append(frame)
pair[0].save(p/'AttackPair.gif',save_all=True,append_images=pair[1:],duration=[33]*19+[330],loop=0)
