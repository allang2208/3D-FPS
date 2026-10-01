import ast,json
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).parent;O=HERE.parent/'G18Integration20260929'
geo=json.loads((HERE/'icon_geometry.json').read_text());N=768
tree=ast.parse((O/'author_icons.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='raster'],type_ignores=[]),'G18 source raster','exec'))
out=HERE/'Icons';out.mkdir(exist_ok=True)
dest=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
names={'ext_mag':'magazine_ext_mag','holographic':'optic_holographic','panoramic_red_dot':'optic_panoramic_red_dot'}
for key,option in names.items():
    im=raster(key,grey=True);name='ue_g18_'+option+'.png';im.save(out/name);im.save(dest/name)
print('G18_REPAIRED_PART_ICONS_SAVED')
