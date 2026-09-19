"""Use metal-only receiver texture region from the already licensed Soviet Fab AKM."""
from PIL import Image
from pathlib import Path
import json
O=Path(__file__).parent;source=O.parent/'AKMSoviet20260911/Source/ak47fbx_extracted/textures';out=O/'Metal';out.mkdir(exist_ok=True)
region=(.055,.908,.285,.947)
for kind in ['Base_color','Metallic','Roughness','Normal_OpenGL']:
 im=Image.open(source/f'AK_{kind}.png');box=tuple(round(v*(im.width if i%2==0 else im.height)) for i,v in enumerate(region))
 patch=im.crop(box).resize((1024,256),Image.Resampling.LANCZOS);patch.save(out/f'T_AKM_Mount_{kind}.png')
(out/'provenance.json').write_text(json.dumps({'source':'https://www.fab.com/listings/d14e05e8-553a-409a-8df0-7c9a8d2c69f4','local_source':str(source),'crop_image_coordinates':region,'usage':'AKM fabricated optic bridge only; receiver metal patch, no wood or hardware atlas islands'},indent=2))
