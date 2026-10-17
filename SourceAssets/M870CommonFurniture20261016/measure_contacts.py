import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Inputs/Native_Edit.blend'),use_scripts=False)
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
# stock-only region vertices in actual original mesh
vs=[v.co for v in o.data.vertices if v.co.y<-.163 and abs(v.co.x)<.022 and -.91<v.co.z<-.71]
print('STOCK STATIONS')
for y in (-.163,-.17,-.18,-.19,-.20,-.21,-.22,-.23,-.24,-.25,-.26,-.27,-.28,-.30):
 ps=[]
 for e in o.data.edges:
  a,b=[o.data.vertices[i].co for i in e.vertices]
  if (a.y-y)*(b.y-y)<0 and -.91<a.z<-.71 and -.91<b.z<-.71:
   ps.append(a.lerp(b,(y-a.y)/(b.y-a.y)))
 print(y,[[min(p[j] for p in ps),max(p[j] for p in ps)] for j in (0,2)] if ps else None)
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')),use_anim=False)
 ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.data.transform(ob.matrix_world)
 print('DONOR',key,[m.name for m in ob.data.materials],[[min(v.co[j] for v in ob.data.vertices),max(v.co[j] for v in ob.data.vertices)] for j in range(3)])
