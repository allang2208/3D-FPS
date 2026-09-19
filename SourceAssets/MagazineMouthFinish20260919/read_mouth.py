import bpy,bmesh,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ExtMagContact20260919/AKM_ExtMag_Closed_Editable.blend'))
ob=bpy.data.objects['SM_ExtMag_AKM40_Closed'];bm=bmesh.new();bm.from_mesh(ob.data)
edges={e for e in bm.edges if e.is_boundary and max(v.co.z for v in e.verts)>-.19};groups=[]
while edges:
 e=edges.pop();component={e};stack=list(e.verts)
 while stack:
  v=stack.pop()
  for edge in v.link_edges:
   if edge in edges:edges.remove(edge);component.add(edge);stack.extend(edge.verts)
 vs={v for e in component for v in e.verts}
 groups.append({'edges':len(component),'bounds':[[min(v.co[j] for v in vs),max(v.co[j] for v in vs)] for j in range(3)],'points':[list(v.co) for v in vs]})
(O/'mouth_boundaries.json').write_text(json.dumps(groups,indent=2))
print(json.dumps([{k:v for k,v in g.items() if k!='points'} for g in groups],indent=2))
from mathutils import Vector
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='SINGLE';s.display.shading.show_cavity=True
c=bpy.data.objects.new('MouthDiagnosis',bpy.data.cameras.new('MouthDiagnosis'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.1
center=Vector((.06,.19,-.097));c.location=center+Vector((-.10,-.1,.13));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=500;s.render.resolution_y=500;s.render.resolution_percentage=100;s.render.filepath=str(O/'mouth_before.png');bpy.ops.render.render(write_still=True)
