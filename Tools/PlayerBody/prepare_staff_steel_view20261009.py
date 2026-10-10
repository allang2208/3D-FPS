"""Prepare scoped author-space views for the requested grip/armor diagnosis."""
import sys
from staff_thumb_steel_math import *
label=sys.argv[1]
geo=read('SourceAssets/ThirdPersonStaffThumbSteel20261009/'+sys.argv[2]+'.json')
grip=read(sys.argv[3] if len(sys.argv)>3 else 'SourceAssets/ThirdPersonStaffGripFacing20261009/authored-grip.json')['variants']['false']
w=pose(grip)
p=skin(geo,w);tri=np.array(geo['triangles'],int)
mask=np.array([sum(v for b,v in ws if names[b].endswith('_r'))>.95 for ws in geo['weights']])
keep=np.all(mask[tri],axis=1)
(OUT/(label+'-view.json')).write_text(json.dumps(dict(positions=p.tolist(),triangles=tri[keep].tolist(),materials=np.array(geo['triangle_materials'])[keep].tolist())))
print('AUTHOR_VIEW_READY',label)
