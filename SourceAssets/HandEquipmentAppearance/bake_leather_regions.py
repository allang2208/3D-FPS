"""Rasterize hand regions and stitches from existing mesh geometry; no scan is generated."""
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT = Path(__file__).parent
SIZE = 4096
metrics = json.loads((OUT/'geometry_metrics.json').read_text())
uv_per_metre = math.sqrt(metrics['total_uv_area']/metrics['total_mesh_area'])
px_per_metre = uv_per_metre * SIZE
glove = Image.new('L',(SIZE,SIZE),0)
palm = Image.new('L',(SIZE,SIZE),0)
stitches = Image.new('L',(SIZE,SIZE),0)
dg, dp, ds = ImageDraw.Draw(glove),ImageDraw.Draw(palm),ImageDraw.Draw(stitches)
def pixel(uv):
    return (uv[0]*(SIZE-1),(1-uv[1])*(SIZE-1))
faces = json.loads((OUT/'region_faces.json').read_text())
for face in faces:
    points = [pixel(p) for p in face['uv']]
    dg.polygon(points, fill=255)
    if face['palm']:
        dp.polygon(points, fill=255)
for seg in json.loads((OUT/'seam_segments.json').read_text()):
    if seg['palm'] or seg['length'] < 1e-7:
        continue
    a, b, c = np.array(seg['a']), np.array(seg['b']), np.array(seg['inside'])
    tangent = b-a
    inward = np.array([-tangent[1],tangent[0]])
    inward /= max(np.linalg.norm(inward),1e-9)
    if np.dot(inward,c-(a+b)/2)<0:
        inward = -inward
    inset = inward * .0012 * uv_per_metre
    start, end = seg['distance'], seg['distance']+seg['length']
    pitch, dash = .0032, .0019
    for n in range(math.floor(start/pitch),math.ceil(end/pitch)):
        lo, hi = max(start,n*pitch), min(end,n*pitch+dash)
        if hi <= lo:
            continue
        p = a+tangent*((lo-start)/seg['length'])+inset
        q = a+tangent*((hi-start)/seg['length'])+inset
        ds.line([pixel(p),pixel(q)], fill=255,width=max(1,round(.00048*px_per_metre)))
stitches = ImageChops.multiply(stitches,glove)
glove = glove.filter(ImageFilter.MaxFilter(9))
palm = palm.filter(ImageFilter.MaxFilter(9))
stitches = stitches.filter(ImageFilter.GaussianBlur(.55))
Image.merge('RGB',(glove,palm,stitches)).save(OUT/'T_Manny_LeatherRegions.png')
# DirectX tangent-space normal for a low raised thread; the source fold normal
# and downloaded scan normal are blended in UE, not overwritten by this map.
height = np.asarray(stitches,dtype=np.float32)/255
dy, dx = np.gradient(height)
nx, ny = -dx*.65, -dy*.65
nz = np.ones_like(nx)
norm = np.sqrt(nx*nx+ny*ny+nz*nz)
normal = np.stack((nx/norm,ny/norm,nz/norm),axis=-1)
Image.fromarray(np.uint8(np.clip((normal*.5+.5)*255,0,255))).save(OUT/'T_Manny_StitchNormal.png')
report = {'glove_faces':len(faces),'palm_faces':sum(f['palm'] for f in faces),
          'mask_channels':{'R':'all gloves','G':'palm and finger pads','B':'dorsal shell-edge stitches'},
          'scan_width_metres':.25,'leather_uv_repeat':metrics['leather_uv_repeat_for_25cm_scan'],
          'stitch_pitch_metres':.0032,'stitch_width_metres':.00048,
          'status':'authoring masks only; no Fab scan imported or runtime material applied'}
(OUT/'regions_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
