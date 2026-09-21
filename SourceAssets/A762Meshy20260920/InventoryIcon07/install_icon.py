"""Install only the A762 catalog PNG and catalog reference, preserving other items."""
from pathlib import Path
import json,re,shutil,hashlib
from PIL import Image
O=Path(__file__).parent;R=O.parents[2]
image=Image.open(O/'ue_a762.png');image.load()
assert image.mode=='RGBA' and image.size==(768,320)
assert image.getchannel('A').getbbox() is not None,'Empty icon'
png=R/'Content/ColdSteelData/Icons/ue_a762.png'
(O/'Before').mkdir(exist_ok=True)
if png.exists() and not (O/'Before/ue_a762.png').exists():shutil.copy2(png,O/'Before/ue_a762.png')
shutil.copy2(O/'ue_a762.png',png)
catalog=R/'Content/ColdSteelData/items.json';text=catalog.read_text(encoding='utf-8')
start=text.index('  "ue_a762": {');tail=text[start:]
tail,count=re.subn(r'("ue_icon"\s*:\s*)"[^"]*"',r'\1"Icons/ue_a762.png"',tail,count=1)
assert count==1
catalog.write_text(text[:start]+tail,encoding='utf-8')
assert json.loads(catalog.read_text(encoding='utf-8'))['ue_a762']['ue_icon']=='Icons/ue_a762.png'
report={'definition':'ue_a762','png':str(png),'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'size':list(image.size),'alpha_bounds':list(image.getchannel('A').getbbox()),'data_reference':'Icons/ue_a762.png','dynamic_icon_fix':'Exclude handguard from hand material filtering','native_compile':'pending: see native_compile_01.txt','game_tested':False}
(O/'DELIVERY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('A762_CATALOG_PNG_AND_REFERENCE_INSTALLED')
