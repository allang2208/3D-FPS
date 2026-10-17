import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'M870UrbanAnimations20261015/Original/870'
bpy.ops.wm.open_mainfile(filepath=str(S/'Renmington 870 unfucked.blend'),use_scripts=False)
data={}
for name in ('shell for animating ','shell','shotgun','c_arms_combine'):
 ob=bpy.data.objects[name];names={g.index:g.name for g in ob.vertex_groups};used={}
 positions=[];weights=[]
 for v in ob.data.vertices:
  w={names[g.group]:g.weight for g in v.groups if g.weight>0}
  for n,value in w.items():used[n]=used.get(n,0)+value
  positions.append(list(ob.matrix_world@v.co));weights.append(w)
 data[name]={'positions':positions,'weights':weights,'faces':[list(f.vertices) for f in ob.data.polygons]}
 print('SOURCE_BIND_SURFACE',name,sorted(used.items(),key=lambda v:-v[1])[:8],flush=True)
r=bpy.data.objects['gmod_arms'];data['bone_tails']={b.name:list(r.matrix_world@b.tail_local) for b in r.data.bones}
(O/'reference_surfaces.json').write_text(json.dumps(data,separators=(',',':')))
