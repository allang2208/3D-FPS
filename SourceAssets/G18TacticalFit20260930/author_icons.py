"""Regenerate the two delivered catalog icons from their relocated meshes."""
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
for kind in ('laser','flashlight'):
    im=raster(kind,grey=True);name='ue_g18_tactical_'+kind+'.png';im.save(out/name);im.save(dest/name)
print('G18_TACTICAL_ICONS_SAVED')
