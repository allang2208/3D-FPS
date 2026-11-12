"""Label unretouched matching-time runtime-skin views for the handoff."""
from pathlib import Path
from PIL import Image,ImageDraw
here=Path(__file__).resolve().parent
old=here.parent/'Wrist37/FollowupReview/contact'
new=here/'contact_clearance';out=here/'review';out.mkdir(exist_ok=True)
canvas=Image.new('RGB',(1600,1260),'#202020');draw=ImageDraw.Draw(canvas)
for row,(name,label) in enumerate([('box_normal_base_022_outside.png','Normal reload / source 4.377'),
                                   ('box_empty_base_022_outside.png','Empty reload / source 3.484')]):
    for col,folder in enumerate([old,new]):
        image=Image.open(folder/name).convert('RGB')
        canvas.paste(image,(col*800,row*630+30))
        draw.text((col*800+8,row*630+8),f'{"W37 before" if col==0 else "W38 saved"} | {label}',fill='white')
canvas.save(out/'right_approach_before_after.jpg',quality=95)
