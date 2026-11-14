"""Keep the original pixels and identical framing; lay out the two UE captures side by side."""
from pathlib import Path
import sys,json
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
name=sys.argv[1]
def metadata(stage):return json.loads((R/(stage+'-capture.json')).read_text('utf8'))[0]
a,b=metadata('before'),metadata(name)
for k in ('eye','rotation','fov','frame_width','frame_height'):
    if a[k]!=b[k]:raise ValueError('Camera mismatch '+k)
imgs=[Image.open(R/row['file']).convert('RGB') for row in (a,b)]
if imgs[0].size!=imgs[1].size:raise ValueError('Frame mismatch')
w,h=imgs[0].size;border=24;top=82;gap=24
out=Image.new('RGB',(2*w+gap+border*2,h+border+top),(35,35,34))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',37)
draw=ImageDraw.Draw(out)
for i,(label,im) in enumerate(zip(['修改前','修改后'],imgs)):
    x=border+i*(w+gap);draw.text((x,15),label,font=font,fill=(237,234,226));out.paste(im,(x,top))
out.save(R/(sys.argv[2] if len(sys.argv)>2 else 'OppositePlatform-Before-After.jpg'),quality=96,subsampling=0)
