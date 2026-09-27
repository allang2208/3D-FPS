"""Authoring dimensions for moving the arrow beside the wooden grip."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'SourceAssets/DarkBow20260925/ReferenceUpgradeV10/author_actions.py'
ns={'__file__':str(source)}
exec(compile(source.read_text(encoding='utf-8').split('bpy.ops.wm.read_factory_settings(use_empty=True)')[0],str(source),'exec'),ns)
pose=ns['pose']('Idle',0.)
to_bow=pose['bow_grip'].inverted()
skin={n:to_bow@pose[n]@ns['rest'][n].inverted() for n in pose}
points={d:[] for d in ('index','middle','thumb')}
for p,weights in zip(ns['data']['positions'],ns['data']['weights']):
    for digit in points:
        if sum(w for n,w in weights.items() if n.startswith(digit+'_') and n.endswith('_l'))<.5:continue
        rest=ns['R']@Vector(p)
        point=sum((skin[n]@rest*w for n,w in weights.items()),Vector())
        points[digit].append(point)
def bounds(values):
    return {'min':[min(v[i] for v in values) for i in range(3)],'max':[max(v[i] for v in values) for i in range(3)]}
report={'left_digits_cm':{d:bounds(v) for d,v in points.items()}}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/DarkBow20260925/WoodLongbow20260925/WoodLongbow_Editable.blend'))
obj=bpy.data.objects['SM_DarkBow_WoodLongbow']
scale=100. if max(obj.dimensions)<5 else 1.
verts=[Vector((v.co.x,-v.co.y,v.co.z))*scale for v in obj.data.vertices]
report['bow_slices_cm']={str(z):bounds([v for v in verts if abs(v.z-z)<.4]) for z in (1.5,4.,5.5,6.5,7.5)}
out=ROOT/'Saved/BowModelRepair20260926/arrow-rest-dimensions.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BOW_ARROW_REST_DIMENSIONS',json.dumps(report),flush=True)
