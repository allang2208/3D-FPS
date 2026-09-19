import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'))
report={}
for arm in [o for o in bpy.data.objects if o.type=='ARMATURE']:
 bones=arm.data.bones
 if not bones.get('WPN_RearSight'):continue
 rear=arm.matrix_world@bones['WPN_RearSight'].matrix_local
 front=arm.matrix_world@bones['WPN_FrontSight'].matrix_local
 forward=(front.translation-rear.translation).normalized();up=rear.to_quaternion()@Vector((0,0,1));side=forward.cross(up).normalized()
 def project(v):
  d=v-rear.translation
  return [d.dot(forward),d.dot(side),d.dot(up)]
 report['bones']={b.name:project((arm.matrix_world@b.matrix_local).translation) for b in bones if any(x in b.name.lower() for x in ['wpn','hand_l','palm','index_01_l'])}
 report['materials']={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  groups={}
  for poly in o.data.polygons:
   name=o.material_slots[poly.material_index].name if o.material_slots else o.name
   groups.setdefault(name,set()).update(poly.vertices)
  for name,indices in groups.items():
   pts=[project(o.matrix_world@o.data.vertices[i].co) for i in indices]
   report['materials'][o.name+'/'+name]={'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)]}
 break
(P/'rifle_frame.json').write_text(json.dumps(report,indent=2))
print('PRISM_RIFLE_PROBE_PASS')
