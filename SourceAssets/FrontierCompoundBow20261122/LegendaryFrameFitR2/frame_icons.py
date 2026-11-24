from pathlib import Path
import sys
from PIL import Image,ImageOps
root,batch=map(Path,sys.argv[1:])
src=Path(__file__).resolve().parent
frame=Image.open(root/'SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png').convert('RGBA').resize((1024,1024),Image.Resampling.LANCZOS)
for kind in ('Eclipse','Aurora'):
    part=Image.open(batch/(kind+'-after-icon.png')).convert('RGBA')
    gray=ImageOps.grayscale(part).point(lambda a:round(255*(a/255)**.78))
    result=Image.alpha_composite(frame,Image.merge('RGBA',(gray,gray,gray,part.getchannel('A'))))
    tone=ImageOps.grayscale(result)
    Image.merge('RGBA',(tone,tone,tone,result.getchannel('A'))).save(src/'Export'/('bow_frontier_compound_riser_frontier_'+kind.lower()+'.png'))
