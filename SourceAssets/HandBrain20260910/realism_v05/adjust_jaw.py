import math
from mathutils import Matrix, Quaternion, Vector
body=bpy.data.objects['HandBrain_Body']
# Give the attached oral lining a usable unwrap; the original lining had zero-area UVs.
uv=body.data.uv_layers.active
for face in body.data.polygons:
 if face.material_index!=1:continue
 coords=[]
 for vi in face.vertices:
  x,y,z=body.data.vertices[vi].co
  u=(math.atan2((z-.758)/.004,y/.245)/math.tau)%1
  coords.append([u,max(.02,min(.98,(.72-x)/.55))])
 if max(c[0] for c in coords)-min(c[0] for c in coords)>.5:
  for c in coords:
   if c[0]<.5:c[0]+=1
 for li,c in zip(face.loop_indices,coords):uv.data[li].uv=c
changes=0
for v in body.data.vertices:
 t=body.data.attributes['lip_band_t'].data[v.index].value
 split=body.data.attributes['lip_band_split'].data[v.index].value
 if t>0 and split<.5:
  v.co.x+=.012*math.sin(math.pi*t)*((.5-split)*2)
  changes+=1
 # Extend coherent jaw movement into chin, instead of stretching its upper edge.
 x,y,z=v.co
 if x>.40 and abs(y)<.30 and .35<z<.69:
  boost=.22*math.sin(math.pi*(z-.35)/.34)**2*max(0,1-(abs(y)/.30)**4)
  for parent in ['base','neck','cranium']:
   g=body.vertex_groups.get(parent);j=body.vertex_groups.get('mouth_jaw_'+parent)
   if not g or not j:continue
   weights={e.group:e.weight for e in v.groups};w=weights.get(g.index,0)
   if w>0:
    g.add([v.index],w*(1-boost),'REPLACE');j.add([v.index],weights.get(j.index,0)+w*boost,'REPLACE')
a=bpy.data.actions['Attack_Howl'];rig.animation_data.action=a
rig.animation_data.action_slot=a.slots[0]
def envelope(t):
 keys=[(0,0),(.08,0),(.25,.18),(.48,.65),(.82,1),(1.8,1),(2.18,.52),(2.62,0),(3,0)]
 for (x,u),(y,v) in zip(keys,keys[1:]):
  if t<=y:
   q=max(0,min(1,(t-x)/(y-x)));q=q*q*(3-2*q);return u+(v-u)*q
 return 0
pivot=Vector((.20,0,.83))
for f in range(1,92):
 s.frame_set(f);amount=envelope((f-1)/30)
 for parent in ['base','neck','cranium']:
  p=rig.pose.bones['mouth_jaw_'+parent];rest=p.bone.matrix_local
  turn=Quaternion((0,1,0),math.radians(29)*amount).to_matrix().to_4x4()
  delta=Matrix.Translation(pivot+Vector((-.012,0,-.018))*amount)@turn@Matrix.Translation(-pivot)
  p.matrix_basis=rest.inverted()@delta@rest;p.rotation_mode='QUATERNION'
  for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f)
  for part,factor in [('upper',.76),('cheek_L',.65),('cheek_R',.65)]:
   p=rig.pose.bones['mouth_'+part+'_'+parent];p.location*=factor;p.keyframe_insert('location',frame=f)
(OUT/'jaw_report.json').write_text(json.dumps({'lip_vertices_refined':changes,'jaw_rotation_deg':29,'pivot_m':list(pivot),'howl_seconds':3,'full_open_seconds':[.82,1.8],'closed_seconds':2.62,'other_actions_modified':False},indent=2))
