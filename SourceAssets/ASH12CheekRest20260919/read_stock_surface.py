"""Read the actual ASH receiver surface for a fitted cosmetic cheek rest."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
I=json.loads((O.parent/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
F=Matrix(I['rail_frame'])
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['ASH12_Export']
T=F.inverted()@r.matrix_world.inverted()@gun.matrix_world
points=[T@v.co for v in gun.data.vertices]
result={'frame':I['rail_frame'],'root':I['root_rest'],'materials':{},'sections':[]}
def bounds(p):return [[round(min(v[i] for v in p),6),round(max(v[i] for v in p),6)] for i in range(3)] if p else None
for mi,mat in enumerate(gun.data.materials):
 ids={i for f in gun.data.polygons if f.material_index==mi for i in f.vertices}
 result['materials'][mat.name]={'bounds':bounds([points[i] for i in ids]),'vertices':len(ids)}
for j in range(-36,3):
 x=j*.01;p=[v for v in points if abs(v.x-x)<.005]
 result['sections'].append({'x':x,'bounds':bounds(p),'top':bounds([v for v in p if v.z>-.09])})
result['bones']={b.name:list(F.inverted()@b.head_local) for b in r.data.bones if b.name.startswith('WPN')}
tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in gun.data.polygons])
result['surface_samples']=[]
for x in (-.311,-.30,-.28,-.26,-.24,-.22,-.20,-.18,-.16,-.14):
 top=[]
 for y in (-.021,-.019,-.015,-.01,0,.01,.015,.019,.021):
  hit,_,_,_=tree.ray_cast(Vector((x,y,.02)),Vector((0,0,-1)),.3)
  top.append([y,list(hit) if hit else None])
 side=[]
 for z in (-.06,-.065,-.07,-.075,-.08,-.085,-.09):
  for s in (-1,1):
   hit,_,_,_=tree.ray_cast(Vector((x,s*.06,z)),Vector((0,-s,0)),.09)
   side.append([z,s,list(hit) if hit else None])
 result['surface_samples'].append({'x':x,'top':top,'side':side})
(O/'stock_surface.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result['surface_samples']),flush=True)
