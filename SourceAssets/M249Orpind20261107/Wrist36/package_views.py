from pathlib import Path
from PIL import Image,ImageDraw
import json
ROOT=Path(__file__).resolve().parent;views=ROOT/'native_views';out=ROOT/'review';out.mkdir(exist_ok=True)
def sheet(items,path,cols=3,width=500):
    height=380;cell=height+30;im=Image.new('RGB',(cols*width,((len(items)+cols-1)//cols)*cell),'#202020');draw=ImageDraw.Draw(im)
    for k,(file,label) in enumerate(items):
        tile=Image.open(file).convert('RGB');tile.thumbnail((width,height));x=k%cols*width;y=k//cols*cell;im.paste(tile,(x,y+30));draw.text((x+8,y+8),label,fill='white')
    im.save(path)
families=['base','vertical','tactical_vertical','angled','canted','prism']
for empty in [False,True]:
    mode='empty' if empty else 'normal'
    for stage in ['hold','support','regrip','free','cover']:
        for angle in ['palm','outside']:
            items=[(views/f'box_{mode}_{f}_{stage}_{angle}.png',f'{f} / {mode} / {stage}') for f in families]
            sheet(items,out/f'{mode}_{stage}_{angle}.jpg')
    items=[(views/f'box_{mode}_base_belt_{stage}_{angle}.png',f'{mode} / belt {stage} / {angle}') for angle in ['palm','outside'] for stage in ['pick','lift','place']]
    sheet(items,out/f'{mode}_right_belt.jpg')
(out/'capture.json').write_text((views/'capture.json').read_text())
print('PACKAGED',len(list(out.glob('*.jpg'))),'actual-skin sheets')
