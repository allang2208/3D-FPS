"""Measure captured pixels and logged projection; retain the original PNGs."""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image,ImageDraw

root=Path(sys.argv[1])
capture=json.loads((root/'capture.json').read_text(encoding='utf-8-sig'))
rows=capture['frames'];by_name={r['image']:r for r in rows}
report={'capture_complete':capture['complete'],'frame_count':len(rows),
        'missing_images':[r['image'] for r in rows if not (root/r['image']).exists()],
        'coverage_masks':[]}

def polygon(shape,points):
    im=Image.new('1',(shape[1],shape[0]));ImageDraw.Draw(im).polygon([tuple(x) for x in points],fill=1)
    return np.array(im,dtype=bool)

for row in rows:
    if not row.get('coverage_mask'):continue
    a=np.asarray(Image.open(root/row['image']).convert('RGB')).astype(np.int16)
    boundary=np.array(row['projected_lens_boundary']);center=boundary.mean(axis=0)
    # Drop the thin anti-aliased rim from the interior measurement; report the
    # separate outer margin explicitly rather than calling bloom a lens leak.
    inner=polygon(a.shape,center+(boundary-center)*.96)
    outer=polygon(a.shape,center+(boundary-center)*1.04)
    green=(a[:,:,1]>200)&(a[:,:,1]>a[:,:,0]+40)&(a[:,:,1]>a[:,:,2]+60)
    visible=inner.copy()
    # Normal combat draw HUD and the etched reticle are expected over the lens.
    visible[425:530,730:875]=False
    visible[565:592,845:898]=False
    points=np.argwhere(green)
    report['coverage_masks'].append(dict(image=row['image'],stage=row['stage'],
        raw_inner_green_fraction=float(green[inner].mean()),
        unobscured_inner_green_fraction=float(green[visible].mean()),
        green_pixels_beyond_4_percent_edge_margin=int((green&~outer).sum()),
        green_bounds_xy=[int(points[:,1].min()),int(points[:,0].min()),int(points[:,1].max()),int(points[:,0].max())],
        projected_bounds_xy=[*boundary.min(axis=0).tolist(),*boundary.max(axis=0).tolist()]))

ads=[r for r in rows if r['aim']>.999]
report['full_ads']=dict(frames=len(ads),world_fov_range=[min(r['world_fov'] for r in ads),max(r['world_fov'] for r in ads)],
    viewmodel_fov_range=[min(r['viewmodel_fov'] for r in ads),max(r['viewmodel_fov'] for r in ads)],
    lens_blend_range=[min(r['lens_blend'] for r in ads),max(r['lens_blend'] for r in ads)],
    styles=sorted(set(r['reticle_style'] for r in ads)))
full3,full6=by_name['03_full_3x.png'],by_name['07_full_6x.png']
for label,row in [('full_3x',full3),('full_6x',full6)]:
    boundary=np.array(row['projected_lens_boundary'])
    report[label]=dict(actual_zoom=row['displayed_zoom'],center_xy=boundary.mean(axis=0).tolist(),
        aperture_width_height=(boundary.max(axis=0)-boundary.min(axis=0)).tolist())
outside=[]
for name in ('03_full_3x.png','07_full_6x.png'):
    a=np.asarray(Image.open(root/name).convert('RGB')).astype(np.float32)
    outside.append(a[400:600,30:500,:])
report['outside_left_scene_abs_difference_0_to_255']=float(np.abs(outside[0]-outside[1]).mean())
report['exit']=dict(first_person_enabled=rows[-1]['first_person_enabled'],viewmodel_fov=rows[-1]['viewmodel_fov'])
report['scope']='One 1600x900 production-map capture; numeric masks plus manual review, not hand-feel or all-map acceptance.'
(root/'image-analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
