"""Extract the user-downloaded Fab texture set and record exact source files."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from PIL import Image

OUT = Path(__file__).parent
ZIP = Path('C:/Users/allan/Downloads/fabric_generic_leather_top_grain_brown_xjghdgl_4k.zip')
DEST = OUT/'Source'
DEST.mkdir(exist_ok=True)
with ZipFile(ZIP) as archive:
    for item in archive.infolist():
        target = (DEST/item.filename).resolve()
        assert target.is_relative_to(DEST.resolve())
        archive.extract(item,DEST)
def find(suffix):
    files = list(DEST.glob('*'+suffix+'.jpg'))
    assert len(files)==1, suffix
    return files[0]
base = find('_BaseColor')
arr = np.asarray(Image.open(base).resize((256,256)),dtype=np.float32)/255
linear = np.where(arr<=.04045,arr/12.92,((arr+.055)/1.055)**2.4)
mid = float(np.median(linear @ np.array([.299,.587,.114])))
height = np.asarray(Image.open(find('_Bump')).convert('L'),dtype=np.float32)
normal_pixels = np.asarray(Image.open(find('_Normal')),dtype=np.float32)-127.5
dy, dx = np.gradient(height)
r_dx = float(np.corrcoef(normal_pixels[::4,::4,0].ravel(),dx[::4,::4].ravel())[0,1])
g_dy = float(np.corrcoef(normal_pixels[::4,::4,1].ravel(),dy[::4,::4].ravel())[0,1])
assert r_dx < -.6 and g_dy > .6, 'Review normal orientation against bump height.'
report = {'listing':'https://www.fab.com/listings/ccd7a956-27f6-4417-b4e0-d1eb92e55ea0',
          'title':'Fabric Generic Leather Top Grain Brown','publisher':'Quixel Megascans',
          'download_package':str(ZIP),'package_sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest(),
          'basecolor':str(base),'normal':str(find('_Normal')),'roughness':str(find('_Roughness')),
          'color_midpoint_linear':mid,'scan_width_metres':.25,
          'normal_convention':'OpenGL','normal_convention_note':'Measured against included bump: R opposes image-X slope, G follows image-Y slope. Flip G on UE import.',
          'normal_height_correlations':{'R_vs_dx':r_dx,'G_vs_dy':g_dy},
          'redistribution':'Licensed local project dependency; original scans not for public source publication.',
          'files':[]}
for path in sorted(DEST.iterdir()):
    report['files'].append({'name':path.name,'bytes':path.stat().st_size,
                             'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'source_maps.json').write_text(json.dumps(report,indent=2))
print('FAB_SOURCE_READY',json.dumps({k:report[k] for k in ('title','color_midpoint_linear','package_sha256')}))
