"""Compare matching actual captures and package every grip's final contact view."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
root=HERE.parent/'Wrist34/geometry_wrist_thirty_eight_final'
prior=HERE.parent/'Wrist34/geometry_wrist_thirty_seven_followup'
out=HERE/'review';out.mkdir(exist_ok=True)
guard={};grips=['base','vertical','tactical_vertical','angled','canted','prism']
for mode in ['normal','empty']:
    shift=.9 if mode=='empty' else 0
    canvas=Image.new('RGB',(4*400,6*249),'#202020');draw=ImageDraw.Draw(canvas)
    for row,grip in enumerate(grips):
        name=f'box_{mode}_{grip}';folder=root/name;old=prior/name
        meta=json.loads((folder/'geometry.json').read_text());dominant=np.fromfile(folder/'dominant.bin',np.uint32)
        left=np.array([n.endswith('_l') for n in meta['bones']])[dominant]
        frames=json.loads((folder/'review.json').read_text())['frames']
        originals=json.loads((old/'review.json').read_text())['frames'];maxchange=0.
        for f,o in zip(frames,originals):
            assert abs(f['source']-o['source'])<1e-6
            a=np.fromfile(folder/Path(f['file']).with_suffix('.vertices'),np.float32).reshape(-1,3)
            b=np.fromfile(old/Path(o['file']).with_suffix('.vertices'),np.float32).reshape(-1,3)
            maxchange=max(maxchange,float(np.max(np.linalg.norm(a[left]-b[left],axis=1))))
        guard[name]=maxchange
        for col,t in enumerate([4.35,4.45,4.8,5.1]):
            f=min(frames,key=lambda x:abs(x['source']-(t-shift)))
            im=Image.open(folder/f['file']).convert('RGB');im.thumbnail((400,225));x=col*400;y=row*249
            canvas.paste(im,(x,y+24));draw.text((x+3,y+5),f'{grip} {mode} {f["source"]:.3f}',fill='white')
    canvas.save(out/f'{mode}_all_grips_final_contact.jpg',quality=94)
assert max(guard.values())<.001
(HERE/'left_skin_preserved.json').write_text(json.dumps(guard,indent=2))
print('Final native left-skin max change cm',max(guard.values()))
