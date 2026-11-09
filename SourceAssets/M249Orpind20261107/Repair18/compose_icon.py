"""Use the 30-round icon's exact border and the existing empty metal plate."""
import json,hashlib
import numpy as np
from PIL import Image,ImageOps,ImageFilter
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2];icons=p/'Content/ColdSteelData/AttachmentIcons20260913'
frame_path=icons/'FramedFirearms/ue_m249_magazine_m249_side_mag_30.png'
blank_path=p/'SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png'
frame=Image.open(frame_path).convert('RGBA');size=frame.size;w,h=size
blank=Image.open(blank_path).convert('RGBA').resize(size,Image.Resampling.LANCZOS)
y,x=np.ogrid[:h,:w];radius=np.hypot((x-.5*w)/w,(y-.49*h)/h)
# Replace only the inset plate and old subject; the actual 30-round border,
# circle and rivets are retained, not redrawn or generated.
mask=Image.fromarray((np.clip((.389-radius)/.014,0,1)*255).astype('uint8'))
plate=Image.composite(blank,frame,mask);plate.putalpha(frame.getchannel('A'))
part=Image.open(r/'Icons/M249_45_Model.png').convert('RGBA');part=part.crop(part.getchannel('A').getbbox())
scale=min(w*.45/part.width,h*.66/part.height);part=part.resize((round(part.width*scale),round(part.height*scale)),Image.Resampling.LANCZOS)
alpha=part.getchannel('A');grey=ImageOps.grayscale(part);part=Image.merge('RGBA',(grey,grey,grey,alpha))
left=(w-part.width)//2;top=round(h*.49-part.height*.5)
shadow_mask=Image.new('L',size);shadow_mask.paste(alpha,(left+round(w*.004),top+round(h*.008)))
shadow=Image.new('RGBA',size,(0,0,0,0));shadow.putalpha(shadow_mask.filter(ImageFilter.GaussianBlur(w*.006)).point(lambda v:round(v*.65)))
plate.alpha_composite(shadow);plate.alpha_composite(part,(left,top))
dest=r/'Icons/ue_m249_magazine_m249_side_mag_45.png';plate.save(dest)
(r/'icon_recipe.json').write_text(json.dumps(dict(model=str(r.parent/'Repair17/Exports/SM_m249_side_mag_45.blend'),frame=str(frame_path),frame_sha256=hashlib.sha256(frame_path.read_bytes()).hexdigest(),blank_plate=str(blank_path),result=str(dest),method='Actual model render, existing 30-round border retained, existing blank plate composited',image_generation=False),indent=2))
print('M249_45_STANDARD_FRAME_COMPOSITED')
