"""Install authored PNGs; keep a scoped pre-change copy."""
from pathlib import Path
from PIL import Image
import json,shutil,hashlib
P=Path(__file__).parent;ROOT=P.parents[1];SRC=P/'Icons';DATA=ROOT/'Content/ColdSteelData'
BACK=ROOT/'Saved/BowModular20260926/Before/Icons';BACK.mkdir(parents=True,exist_ok=True)
rows=[]
names=[]
for c in json.loads((DATA/'bow-gunsmith.json').read_text(encoding='utf8'))['columns']:
    names+=['bow_dark_category_'+c['key'],'bow_dark_'+c['key']+'_false']
    names+=['bow_dark_'+c['key']+'_'+o['id'] for o in c['options']]
for name in names+['bow_dark']:
    whole=name=='bow_dark';source=SRC/('bow_dark_2x.png' if whole else name+'.png')
    folder='Icons' if whole else 'AttachmentIcons20260913';dest=DATA/folder/(name+'.png')
    backup=BACK/(name+'.png')
    if dest.exists() and not backup.exists():shutil.copy2(dest,backup)
    im=Image.open(source).convert('RGBA');size=(640,320) if whole else (1024,1024)
    if im.size!=size:im=im.convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
    dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest)
    rows.append(dict(name=name,png=str(dest),asset_folder='/Game/ColdSteelData/'+folder,size=size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
(P/'icon-install-receipt.json').write_text(json.dumps(dict(pngs=rows,gameplay_tested=False),indent=2),encoding='utf8')
print('BOW_ICONS_INSTALLED',len(rows))
