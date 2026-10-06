"""Bake the original fitted lens region into UV0, independent of imported vertex colours."""
import json
from pathlib import Path
import bpy
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
OUT = PROJECT / 'SourceAssets/BlessedLaser20261006/Repair'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = PROJECT / 'SourceAssets/M1911CompactFit20260913/laser/M1911_Device_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
mesh = bpy.data.objects['SM_TacticalDevice'].data
mesh.calc_loop_triangles()
colors = mesh.color_attributes['MetalRegion']
uvs = mesh.uv_layers[0].data
SIZE = 1024
mask = np.zeros((SIZE, SIZE), dtype=np.float32)
aperture_triangles = 0
for tri in mesh.loop_triangles:
    if tri.material_index != 0:
        continue
    values = np.array([colors.data[i].color[1] for i in tri.loops])
    if values.max() <= 0:
        continue
    uv = np.array([list(uvs[i].uv) for i in tri.loops]) * SIZE
    lo = np.maximum(np.floor(uv.min(axis=0)).astype(int), 0)
    hi = np.minimum(np.ceil(uv.max(axis=0)).astype(int), SIZE - 1)
    if np.any(hi < lo):
        continue
    a, b, c = uv
    denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(denominator) < 1e-10:
        continue
    yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    x, y = xx + 0.5, yy + 0.5
    w0 = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
    w1 = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
    w2 = 1-w0-w1
    inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    coverage = np.where(inside, np.clip(w0*values[0]+w1*values[1]+w2*values[2], 0, 1), 0)
    region = mask[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    np.maximum(region, coverage, out=region)
    aperture_triangles += 1

if aperture_triangles == 0:
    raise RuntimeError('The source has no lens region; refusing an empty mask')
pixels = np.ones((SIZE, SIZE, 4), dtype=np.float32)
pixels[:, :, :3] = mask[:, :, None]
image = bpy.data.images.new('T_LaserApertureMask', width=SIZE, height=SIZE, alpha=False)
image.colorspace_settings.name = 'Non-Color'
image.pixels.foreach_set(pixels.reshape(-1))
image.filepath_raw = str(OUT / 'T_LaserApertureMask.png')
image.file_format = 'PNG'
image.save()
receipt = {'source': str(SOURCE), 'uv': 0, 'source_region': 'MetalRegion.G',
           'aperture_triangles': aperture_triangles, 'size': SIZE,
           'purpose': 'Limit legacy red emission to the authored optical aperture',
           'mask': image.filepath_raw, 'source_modified': False}
(OUT / 'mask-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('LASER_APERTURE_MASK_AUTHORED ' + json.dumps(receipt), flush=True)
