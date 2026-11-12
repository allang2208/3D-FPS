"""Contact sheets made from original UE viewport PNGs, with original materials."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
root=Path(__file__).parent
capture=root.parent/'Wrist34/geometry_wrist_thirty_seven_final'
out=root/'review';out.mkdir(exist_ok=True)
families=['base','vertical','tactical_vertical','angled','canted','prism']
for view in ['wrist_left','wrist_palm']:
    sheet=Image.new('RGB',(1440,6*294),'#202020');draw=ImageDraw.Draw(sheet)
    for y,family in enumerate(families):
        folder=capture/(family+'_'+view);rows=json.loads((folder/'review.json').read_text())['frames']
        for x,time in enumerate([0.,3.,6.49]):
            row=min(rows,key=lambda v:abs(v['source']-time));im=Image.open(folder/row['file']).convert('RGB');im.thumbnail((480,270));sheet.paste(im,(x*480,y*294+24));draw.text((x*480+5,y*294+5),f"{family} source={row['source']:.3f}",fill='white')
    sheet.save(out/(view+'_engine_materials.jpg'))
print('Original-material closeup sheets saved')
