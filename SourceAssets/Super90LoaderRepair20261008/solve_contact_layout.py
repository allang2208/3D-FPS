"""Author loading placement from camera space, reach and neutral wrist axes."""
import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
s={'__file__':str(author)}
code=(O/'Before/Source/author_speedloader.py').read_text().split('def local_rows(')[0]
exec(compile(code,str(author),'exec'),s)
data=json.loads((O/'author_geometry_r3.json').read_text())['camera']
camq=Quaternion(data['rotation']);camloc=Vector(data['location'])
def cam(v):return camloc+camq@Vector((v.x*100,-v.y*100,v.z*100))
def native(v):
    x=camq.inverted()@Vector(v)
    return Vector((x.x/100,-x.y/100,x.z/100))
rest=s['rest'];idle=s['idle'];shoulder=idle['upperarm_l'].translation
a=(idle['lowerarm_l'].translation-shoulder).length;b=(idle['hand_l'].translation-idle['lowerarm_l'].translation).length
rest_axis=rest['hand_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
def solve(wrist):
    hand=wrist.translation;v=hand-shoulder;d=v.length;axis=v.normalized()
    along=(a*a-b*b+d*d)/(2*d);center=shoulder+axis*along
    radius=math.sqrt(max(0.,a*a-along*along))
    wanted=wrist.to_quaternion()@rest_axis
    pole=hand-wanted*b-center;pole-=axis*pole.dot(axis)
    elbow=center+pole.normalized()*radius
    swing=math.degrees((hand-elbow).angle(wanted))
    return swing,cam(elbow),d/(a+b)
best=None
# Keep the contact on this gun. Move the complete weapon action into the
# player's view and choose the palm-bar axial orientation as a single group.
for dx in (12.,16.,20.,24.):
 for dy in (-16.,-12.,-8.):
  for dz in (8.,12.,16.):
   for roll in range(0,360,15):
    offset=native((dx,dy,dz));turn=s['handle_turn']@Matrix.Rotation(math.radians(roll),4,'Z')
    cost=0.;rows=[]
    for f in (87,94,104,114):
     p,_,tube=s['pose'](f,7,False)
     tube.translation+=offset
     stroke=(f-86)/(114-86)
     handle=tube@s['T']((0,-.326+.294*stroke,-.004))@turn
     hand=handle@s['hand_in_handle'];swing,e,reach=solve(hand)
     h=cam(hand.translation);end=cam(tube@Vector((0,-.35,0)))
     cost+=max(0,swing-25)**2+max(0,reach-.94)**2*20000
     cost+=max(0,e.x-32)**2*.6+max(0,e.z+10)**2
     for point in (h,end):
      cost+=max(0,20-point.x)**2*8+max(0,abs(point.y)-point.x*.80)**2*4+max(0,abs(point.z)-point.x*.58)**2*4
     rows.append({'frame':f,'wrist_swing_degrees':swing,'reach':reach,'hand_camera_cm':list(h),'elbow_camera_cm':list(e),'tube_rear_camera_cm':list(end)})
    cost+=dx*.4+abs(dy)*.1+dz*.2
    if best is None or cost<best['cost']:best={'cost':cost,'extra_offset_camera_cm':[dx,dy,dz],'extra_offset_native':list(offset),'handle_axial_roll_degrees':roll,'contacts':rows}
(O/'contact_layout.json').write_text(json.dumps(best,indent=2),encoding='utf-8')
print(json.dumps(best,indent=2),flush=True)
