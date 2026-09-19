import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;data=json.loads((O/'references.json').read_text())
for label,row in data.items():
 b=row['bones'];p={n:Matrix(x['pose']) for n,x in b.items()};rest={n:Matrix(x['rest']) for n,x in b.items()};I=Matrix(row['G']).inverted();v=(p['hand_l'].translation-p['lowerarm_l'].translation).normalized();neutral=p['lowerarm_l'].to_quaternion()@rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion();q=p['hand_l'].to_quaternion()@neutral.inverted();twist=(2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)+math.pi)%(2*math.pi)-math.pi
 d=p['hand_l'].to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
 print(label,'axis-bend',math.degrees(v.angle(d)),'twist',math.degrees(twist),'hand direction',list(I.to_3x3()@d),'positions',{n:[round(x,4) for x in I@p[n].translation] for n in ['upperarm_l','lowerarm_l','hand_l']})
 for n in ['upperarm_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l','index_01_l','index_02_l','index_03_l','middle_01_l','middle_02_l','middle_03_l','ring_01_l','ring_02_l','ring_03_l','pinky_01_l','pinky_02_l','pinky_03_l']:
  q=Matrix(b[n]['basis']).to_quaternion();axis,angle=q.to_axis_angle();print(n,round(math.degrees(angle),2),[round(x,3) for x in axis])
