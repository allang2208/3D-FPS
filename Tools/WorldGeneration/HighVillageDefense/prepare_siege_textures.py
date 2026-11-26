from pathlib import Path
import sys
from PIL import Image
run=Path(sys.argv[1])
folder=next((run/'Downloads'/'Ballista').rglob('Material_Base_color.png')).parent
out=run/'Authored'
def load(name,mode):
    with Image.open(folder/('Material_'+name+'.png')) as im:
        return im.convert(mode).resize((2048,2048),Image.Resampling.LANCZOS)
load('Base_color','RGB').save(out/'T_BallistaBase.png')
load('Normal_DirectX','RGB').save(out/'T_BallistaNormal.png')
Image.merge('RGB',tuple(load(n,'L') for n in ('Mixed_AO','Roughness','Metallic'))).save(out/'T_BallistaORM.png')
