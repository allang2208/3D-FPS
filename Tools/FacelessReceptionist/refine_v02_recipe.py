from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist\author_character_v02.py')
s=p.read_text(encoding='utf-8')
s=s.replace(" # Source arms are separated from the hips by over 15 cm.\n threshold=float(np.interp(p.z,[.75,.98,1.12,1.27,1.40,1.48,1.55],[.29,.28,.245,.205,.155,.135,.18]))\n arm_blend=smooth(threshold-.025,threshold+.025,abs(p.x))",''' # Compare anatomical surface envelopes, including the front/back distance.
 # A height/x-only blend erroneously mixed inner sleeves with the torso.
 shoulder,elbow,wrist=(Vector(TARGET[side][key]) for key in ['shoulder','elbow','wrist'])
 def seg_distance(a,b):
  t=max(0.,min(1.,(p-a).dot(b-a)/(b-a).length_squared))
  return (p-a.lerp(b,t)).length
 arm_metric=min(seg_distance(shoulder,elbow)/.070,seg_distance(elbow,wrist)/.052,
                (p-wrist).length/.16 if p.z<wrist.z else 1e6)
 rx=float(np.interp(p.z,[.8,1.02,1.18,1.34,1.48,1.57],[.205,.18,.143,.16,.13,.055]))
 ry=float(np.interp(p.z,[.8,1.02,1.18,1.34,1.48,1.57],[.14,.14,.11,.14,.10,.055]))
 torso_metric=math.sqrt((p.x/rx)**2+((p.y-.020)/ry)**2)
 arm_blend=smooth(-.35,.35,torso_metric-arm_metric)
 if p.z<1.16 and abs(p.x)<.26:arm_blend=0.''')
s=s.replace("if p.z<bottom or p.z>1.55:return False","if p.z<bottom or p.z>1.62:return False\n   if p.z>1.548 and abs(p.x)<.085:return False")
# Clean the open cuff/hem boundaries before shell extrusion.
s=s.replace("shell(o,.0028 if kind=='jacket' else .0015)","""if kind=='jacket':
  bm=bmesh.new();bm.from_mesh(o.data)
  for v in bm.verts:
   if v.is_boundary and v.co.z<1.025 and abs(v.co.x)<.26:v.co.z=1.005
  bm.to_mesh(o.data);bm.free()
 shell(o,.0028 if kind=='jacket' else .0015)""")
# Envelope from actual original hips avoids painting over or deleting the full body.
s=s.replace("skirt_levels=np.linspace(.475,1.13,40)","""skirt_levels=np.linspace(.475,1.13,40)
skirt_ease=[]
for z in skirt_levels:
 rx=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.27,.255,.245,.23,.195,.160]))
 ry=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.180,.176,.179,.185,.162,.140]))
 region=[p for p in points if abs(p.z-z)<.018 and abs(p.x)<.275]
 cover=max([math.sqrt((p.x/rx)**2+((p.y-.027)/ry)**2) for p in region] or [1.])
 scale=max(1.,cover+.09)
 skirt_ease.append((rx*scale,ry*scale))""")
s=s.replace("rx=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.247,.227,.215,.207,.18,.147]))","rx=float(np.interp(z,skirt_levels,[v[0] for v in skirt_ease]))")
s=s.replace("ry=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.151,.143,.142,.151,.140,.110]))","ry=float(np.interp(z,skirt_levels,[v[1] for v in skirt_ease]))")
s=s.replace("bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()","bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)\n bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()")
s=s.replace("o.data.materials.clear();o.data.materials.append(leather)","""# Reopen the ankle after voxelizing a closed volume.
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(v.co.z>.120 for v in f.verts)],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 o.data.materials.clear();o.data.materials.append(leather)
 for f in o.data.polygons:f.material_index=0
 shell(o,.003)""")
p.write_text(s,encoding='utf-8')
