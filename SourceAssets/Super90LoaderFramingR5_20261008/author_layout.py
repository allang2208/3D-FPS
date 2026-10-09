"""Place loading detail using the actual stock silhouette and native arm reach.

Authoring geometry only; does not run the game, render or accept the result.
"""
import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
author=S/'Super90Speedloader20261007/author_speedloader.py'
code=(O/'Before/Source/author_speedloader.py').read_text().split('def local_rows(')[0]
code=code.replace('math.radians(-7)*phase(f,8,30)',"math.radians(contact_layout.get('gun_yaw_degrees',-7))*phase(f,8,30)")
code=code.replace('math.radians(4)*settle',"math.radians(contact_layout.get('gun_pitch_degrees',4))*settle")
code=code.replace('math.radians(64)*settle',"math.radians(contact_layout.get('gun_roll_degrees',64))*settle")
s={'__file__':str(author)};exec(compile(code,str(author),'exec'),s)
data=json.loads((S/'Super90LoaderRepair20261008/author_geometry_r3.json').read_text())['camera']
cq=Quaternion(data['rotation']);cp=Vector(data['location'])
def cam(p):return cp+cq@Vector((p.x*100,-p.y*100,p.z*100))
def native_delta(v):
    p=cq.inverted()@Vector(v);return Vector((p.x/100,-p.y/100,p.z/100))
eye=native_delta(-cp)
ob=s['bpy'].data.objects['Super90_body'];verts=[ob.matrix_world@v.co for v in ob.data.vertices]
# Back of the receiver to butt: exclude the port itself from stock occlusion.
stock_limit=s['mouth'].y-.12
polys=[tuple(p.vertices) for p in ob.data.polygons if sum(verts[i].y for i in p.vertices)/len(p.vertices)<stock_limit]
stock=BVHTree.FromPolygons(verts,polys)
surface_ids=sorted({i for p in polys for i in p})[::4]
rest=s['rest'];arm_length=sum((s['idle'][a].translation-s['idle'][b].translation).length for a,b in [('lowerarm_l','upperarm_l'),('hand_l','lowerarm_l')])
wrist_axis=rest['hand_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
best=None;choices=[]
for yaw,roll in ((y,r) for y in (-10,10,30,50,70) for r in (64,80,96,112)):
 for pitch in (4,16,28,40):
  for tube_pitch in (28,40,52,64):
   for side in (-10,0,10):
    for height in (-4,0,4):
     for depth in (20,26):
      # Keep the fitted palm/handle relation; solve only the assembly framing.
      s['contact_layout']['gun_yaw_degrees']=yaw;s['contact_layout']['gun_pitch_degrees']=pitch;s['contact_layout']['gun_roll_degrees']=roll
      offset=(float(depth),float(side),float(height));s['contact_layout']['extra_offset_native']=list(native_delta(offset))
      s['tube_bind']=s['T'](s['mouth'])@Matrix.Rotation(math.radians(tube_pitch),4,'X')
      cost=0.;rows=[]
      for frame in (87,100,114):
       p,handle,tube=s['pose'](frame,7,False);inv=rest['WPN_root']@p['WPN_root'].inverted()
       origin=inv@eye;points=[tube@Vector((0,y,0)) for y in (-.025,-.10,-.20,-.30)]+[handle.translation]
       hits=0
       for point in points:
        target=inv@point;v=target-origin;hit=stock.ray_cast(origin,v.normalized(),max(0.,v.length-.004))[0]
        hits+=hit is not None
       hand=p['hand_l'].translation;elbow=p['lowerarm_l'].translation;shoulder=p['upperarm_l'].translation
       swing=math.degrees((hand-elbow).angle(p['hand_l'].to_quaternion()@wrist_axis))
       reach=(hand-shoulder).length/arm_length
       shift=(shoulder-s['idle']['upperarm_l'].translation).length*100
       cost+=hits*3000+max(0,swing-25)**2*4+max(0,reach-.94)**2*30000+max(0,shift-1)**2*100
       camera_points=[cam(x) for x in points]+[cam(hand)]
       # Leave a screen-space margin for the actual palm and tube thickness.
       for c in camera_points:
        cost+=max(0,22-c.x)**2*100+max(0,abs(c.y)-c.x*.75)**2*40+max(0,abs(c.z)-c.x*.48)**2*100
       pose_from_rest=p['WPN_root']@rest['WPN_root'].inverted()
       stock_camera=[cam(pose_from_rest@verts[i]) for i in surface_ids]
       central=sum(1 for c in stock_camera if c.x>0 and abs(c.y/c.x)<.38 and -.35<c.z/c.x<.4)
       cost+=central*2.
       rows.append({'frame':frame,'stock_ray_hits':hits,'central_stock_samples':central,'wrist_swing_degrees':swing,
                    'shoulder_shift_cm':shift,'hand_camera_cm':list(cam(hand)),'mouth_camera_cm':list(cam(tube.translation)),
                    'handle_camera_cm':list(cam(handle.translation))})
      cost+=height*8+abs(side+10)*.6+abs(pitch-4)*.2+abs(tube_pitch-28)*.2+abs(depth-20)*2
      value={'cost':cost,'extra_offset_camera_cm':list(offset),'extra_offset_native':list(native_delta(offset)),
       'handle_axial_roll_degrees':s['contact_layout']['handle_axial_roll_degrees'],
       'gun_yaw_degrees':yaw,'gun_pitch_degrees':pitch,'gun_roll_degrees':roll,'tube_pitch_degrees':tube_pitch,'contacts':rows,
       'method':'Lower right-hand grip; yaw/pitch the stock away from the loading detail; native contact and stock-surface constraints'}
      if best is None or cost<best['cost']:best=value
      choices.append(value)
(O/'contact_layout.json').write_text(json.dumps(best,indent=2),encoding='utf-8')
(O/'layout_choices.json').write_text(json.dumps(sorted(choices,key=lambda v:v['cost'])[:12],indent=2),encoding='utf-8')
print(json.dumps(best,indent=2),flush=True)
