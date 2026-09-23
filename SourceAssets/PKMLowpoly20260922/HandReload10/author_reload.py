"""Reference-directed PKM reload refinement on the current private skeleton.

Explicit contact phases and independently authored finger profiles. Meshes,
rest pose, materials, skin weights and all non-reload actions are retained.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Belt08'))
from belt_dynamics import BeltDynamics,project
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(R/'Belt08/PKM_Gameplay_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];s.render.fps=60;s.render.fps_base=1
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit;Bi=B.inverted()
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
localrest={n:rest[parent[n]].inverted()@m if parent[n] else m.copy() for n,m in rest.items()}
tips=json.loads((R/'Bipod07/fingertips.json').read_text())
grasp=json.loads((R.parent/'MannyGraspDonor20260912/donor_fit.json').read_text())['basis']
layout=json.loads((R/'Belt08/belt_layout.json').read_text());centers=[Vector(c) for c in layout['centers']];N=len(centers);end=layout['inlet_index']
lengths=[(b-a).length for a,b in zip(centers,centers[1:])]
def T(v):return Matrix.Translation(v)
def rot(axis,angle):return Matrix.Rotation(math.radians(angle),4,axis)
def around(p,m):return T(p)@m@T(-Vector(p))
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def seq(t,keys):
 if t<=keys[0][0]:return keys[0][1]
 for (a,v),(b,w) in zip(keys,keys[1:]):
  if t<=b:return v+(w-v)*ramp(t,a,b)
 return keys[-1][1]
def frame(forward,normal):
 x=Vector(forward).normalized();z=Vector(normal);z=(z-x*z.dot(x)).normalized();y=z.cross(x).normalized()
 return Matrix((x,y,z)).transposed()
def mixmat(a,b,x):
 pa,qa,sa=a.decompose();pb,qb,sb=b.decompose()
 return Matrix.LocRotScale(pa.lerp(pb,x),qa.slerp(qb,x),Vector((1,1,1)))
def action(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
action(bpy.data.actions['PKM_Game_idle']);s.frame_set(0);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in r.pose.bones};W0=base['WPN_root']@fit
base_local={n:(base[parent[n]].inverted()@m if parent[n] else m.copy()) for n,m in base.items()}
arm_names=[n for n in rest if any(n.startswith(x) for x in ['clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_'])]
finger_names={side:[n for n in arm_names if n.endswith('_'+side) and any(n.startswith(d+'_') for d in ['thumb','index','middle','ring','pinky'])] for side in ['l','r']}
semantic={};rest_in_hand={}
for side in ['l','r']:
 hand='hand_'+side;H=rest[hand];local={n:H.inverted()@rest[n] for n in finger_names[side]};rest_in_hand[side]=local
 f=local['middle_01_'+side].translation.normalized();radial=(local['index_01_'+side].translation-local['pinky_01_'+side].translation).normalized()
 inward=f.cross(radial).normalized()
 if side=='r':inward.negate()
 semantic[side]={'forward':f,'normal':inward,'frame':frame(f,inward),'palm':local['middle_01_'+side].translation*.56+inward*.011}

# Finger rotations use the actual rest axes. The right thumb is mirrored in
# hand-local anatomical space; raw left-side Euler angles are never copied.
profiles={}
angles={
 'open':{'index':(8,15,8),'middle':(10,18,10),'ring':(15,22,12),'pinky':(18,28,15),'thumb':.25},
 'cover':{'index':(24,62,28),'middle':(28,65,30),'ring':(35,65,32),'pinky':(40,65,35),'thumb':.65},
 'pinch':{'index':(45,80,35),'middle':(45,65,25),'ring':(58,72,35),'pinky':(62,72,35),'thumb':.86},
 'box':{'index':(13,48,30),'middle':(12,52,32),'ring':(17,56,32),'pinky':(20,60,35),'thumb':.72},
 'press':{'index':(5,12,8),'middle':(6,12,8),'ring':(10,16,10),'pinky':(14,20,12),'thumb':.25},
 'charge':{'index':(45,72,30),'middle':(42,68,30),'ring':(54,70,32),'pinky':(58,72,34),'thumb':.7}}

def finger_fk(side,qs):
 matrices={'hand_'+side:Matrix.Identity(4)}
 for n in finger_names[side]:matrices[n]=matrices[parent[n]]@localrest[n]@qs[n].to_matrix().to_4x4()
 return matrices
for side in ['l','r']:
 H=rest['hand_'+side];sem=semantic[side];flex=sem['forward'].cross(sem['normal']).normalized()
 for name,pose in angles.items():
  qs={}
  for n in finger_names[side]:
   digit=n.split('_')[0]
   if digit=='thumb':
    left=n[:-1]+'l';q=Matrix(grasp[left]).to_quaternion()
    if side=='r':
     mirror=H.to_3x3()@Matrix.Diagonal(Vector((-1,-1,-1)))@rest['hand_l'].to_3x3().transposed()
     L=rest[left].to_3x3();Rr=rest[n].to_3x3()
     q=(Rr.transposed()@mirror@L@q.to_matrix()@L.transposed()@mirror.inverted()@Rr).to_quaternion()
    qs[n]=Quaternion().slerp(q,pose['thumb']);continue
   if 'metacarpal' in n:qs[n]=Quaternion();continue
   j=int(n.split('_')[1])-1
   axis=rest[n].to_3x3().transposed()@(H.to_3x3()@flex)
   qs[n]=Quaternion(axis,math.radians(pose[digit][j]))
  # Bounded thumb opposition adjusts only the pinch shape, preserving the
  # authored grasp. No finger translations, scale or unconstrained tip IK.
  if name=='pinch':
   start=dict(qs);best=None
   for a in [-12,-6,0,6,12,18]:
    for b in [-12,-6,0,6,12,18]:
     trial=dict(start)
     for j,amount in [(1,a),(2,b)]:
      n=f'thumb_{j:02}_{side}';axis=rest[n].to_3x3().transposed()@(H.to_3x3()@flex)
      trial[n]=Quaternion(axis,math.radians(amount))@start[n]
     fk=finger_fk(side,trial);ip=fk['index_03_'+side]@Vector(tips['index_03_'+side]['local_tip']);tp=fk['thumb_03_'+side]@Vector(tips['thumb_03_'+side]['local_tip'])
     loss=abs((ip-tp).length-.015)+.000005*(a*a+b*b)
     if best is None or loss<best[0]:best=(loss,trial)
   qs=best[1]
  fk=finger_fk(side,qs)
  if name in ['pinch','charge']:
   anchor=((fk['index_03_'+side]@Vector(tips['index_03_'+side]['local_tip']))+(fk['thumb_03_'+side]@Vector(tips['thumb_03_'+side]['local_tip'])))*.5
  else:anchor=sem['palm']
  profiles[side,name]={'q':qs,'anchor':anchor}

def hand_contact(side,point,forward,normal,profile):
 rotation=frame(forward,normal)@semantic[side]['frame'].transposed()
 m=rotation.to_4x4();m.translation=Vector(point)-rotation@profiles[side,profile]['anchor']
 return {'m':m,'q':profiles[side,profile]['q']}
def ready_hand(side):
 return {'m':W0.inverted()@base['hand_'+side],
         'q':{n:(localrest[n].inverted()@base_local[n]).to_quaternion() for n in finger_names[side]}}
def blend_hand(a,b,x):return {'m':mixmat(a['m'],b['m'],x),'q':{n:a['q'][n].slerp(b['q'][n],x) for n in a['q']}}
def transform_hand(h,m):return {'m':m@h['m'],'q':h['q']}
def hand_seq(t,keys,targets):
 if t<=keys[0][0]:return targets[keys[0][1]]
 for (ta,ka),(tb,kb) in zip(keys,keys[1:]):
  if t<=tb:return blend_hand(targets[ka],targets[kb],ramp(t,ta,tb))
 return targets[keys[-1][1]]

# Work from the current idle assembly, preserving its exact start/end pose.
# Shoulder motion is a small continuous viewmodel reach, and the elbow pole
# is expressed in gun space rather than the old fixed world-space vector.
def arm_pose(side,hand,W,t,working):
 neutral={n:W@W0.inverted()@base[n] for n in arm_names if n.endswith('_'+side)}
 result={n:m.copy() for n,m in neutral.items()};upper='upperarm_'+side;lower='lowerarm_'+side;wrist='hand_'+side;clav='clavicle_'+side
 active=working
 high=seq(t,[(0,0),(.5,1),(1.03,1),(1.3,0)]) if side=='l' else seq(t,[(0,0),(4.9,0),(5.22,1),(5.8,1),(6,0)])
 offset=W.to_3x3()@Vector((-.018 if side=='l' else -.035,-.045-.065*high,-.018 if side=='l' else -.035))
 offset*=active
 for n in result:result[n].translation+=offset
 shoulder=result[upper].translation.copy();old_elbow=neutral[lower].translation;old_wrist=neutral[wrist].translation
 l1=(neutral[lower].translation-neutral[upper].translation).length;l2=(old_wrist-old_elbow).length
 target=W@hand['m'];direction=target.translation-shoulder;distance=direction.length
 direction.normalize();reach=min(l1+l2-.001,max(abs(l1-l2)+.001,distance));wrist_point=shoulder+direction*reach
 pole=W.to_3x3()@Vector((.9 if side=='l' else -.9,.12,-.75));pole-=direction*pole.dot(direction);pole.normalize()
 along=(l1*l1-l2*l2+reach*reach)/(2*reach);elbow=shoulder+direction*along+pole*math.sqrt(max(0,l1*l1-along*along))
 oldaxis=neutral[lower].translation-neutral[upper].translation;newaxis=elbow-shoulder
 swing=oldaxis.rotation_difference(newaxis);m=swing.to_matrix().to_4x4()@neutral[upper];m.translation=shoulder;result[upper]=m
 # Choose forearm roll from the palm orientation. Its deformation helpers
 # follow the whole forearm, avoiding a collapsed ring at the wrist.
 oldaxis=(old_wrist-old_elbow).normalized();newaxis=(wrist_point-elbow).normalized()
 oldnormal=neutral[wrist].to_3x3()@semantic[side]['normal'];newnormal=target.to_3x3()@semantic[side]['normal']
 orient=frame(newaxis,newnormal)@frame(oldaxis,oldnormal).transposed()
 m=orient.to_4x4()@neutral[lower];m.translation=elbow;result[lower]=m
 target.translation=wrist_point;result[wrist]=target
 for segment in ['upperarm','lowerarm']:
  p=segment+'_'+side;delta=result[p]@neutral[p].inverted()
  for n in result:
   if n.startswith(segment+'_twist_'):result[n]=delta@neutral[n]
 for n in finger_names[side]:result[n]=result[parent[n]]@localrest[n]@hand['q'][n].to_matrix().to_4x4()
 # Blend in local joint space to preserve limb segments during the handoff.
 out={}
 for n in result:
  p=parent[n];baseline_local=neutral[p].inverted()@neutral[n] if p in neutral else neutral[n]
  target_local=result[p].inverted()@result[n] if p in result else result[n]
  local=mixmat(baseline_local,target_local,active)
  out[n]=out[p]@local if p in out else local
 return out

hinge=Vector((0,-.021,.07));pivot=Vector((0,.04,-.065));off=Vector((-.22,.24,-.34))
def cover_matrix(t):return around(hinge,rot('X',seq(t,[(0,0),(.65,0),(1.12,108),(5.25,108),(5.72,0),(7.5,0)])))
def curve_frame(c,i):
 x=(c[min(i+1,len(c)-1)]-c[max(0,i-1)]).normalized();return frame(x,Vector((0,1,0)).cross(x)).to_4x4()
rest_frames=[curve_frame(centers,i) for i in range(N)]
def hanging_points():
 a=Vector((-.125,.038224,.018));b=Vector((-.165,.038224,-.016));c=Vector((-.139,.038224,-.092));d=centers[end]
 return [a*(1-u)**3+b*3*u*(1-u)**2+c*3*u*u*(1-u)+d*u**3 for u in [i/end for i in range(end+1)]]
hang=hanging_points()
def belts(t,W,boxes,solvers):
 all_matrices={};tip_positions={}
 for prefix in ['', 'New_']:
  box=boxes[prefix]
  if not prefix:
   hang_amount=ramp(t,1.75,2.12)
   tip=seq(t,[(0,centers[0]),(1.38,centers[0]),(1.65,centers[0]+Vector((-.025,0,.052))),(1.8,Vector((-.06,.038224,.105))),(2.12,hang[0])])
  else:
   hang_amount=1-ramp(t,4.65,5.10)
   tip=seq(t,[(0,hang[0]),(4.48,hang[0]),(4.7,Vector((-.095,.038224,.095))),(4.87,Vector((-.036,.038224,.125))),(5.10,centers[0])])
  pts=[box@p for p in centers];guide=[box@centers[i].lerp(hang[i],hang_amount) for i in range(end+1)]
  guide=project(guide,lengths[:end],box@tip,pts[end],100)
  activation=(ramp(t,1.35,1.55) if not prefix else ramp(t,3.6,4.05))*(1-ramp(t,5.1,5.35))
  pts[:end+1]=solvers[prefix].step(guide,W,activation);tip_positions[prefix]=pts[0]
  for i,p in enumerate(pts):
   orientation=curve_frame(pts,i).to_3x3()@rest_frames[i].to_3x3().transposed();m=orientation.to_4x4();m.translation=p
   all_matrices[prefix+f'PKM_Belt_{i:02}']=W@m
  axis=box.to_3x3()@Vector((0,1,0))
  for i in range(N-1):
   x=(pts[i+1]-pts[i]).normalized();y=(axis-x*axis.dot(x)).normalized();z=x.cross(y).normalized();m=Matrix((x,y,z)).transposed().to_4x4();m.translation=(pts[i]+pts[i+1])*.5
   all_matrices[prefix+f'PKM_Belt_Link_{i:02}']=W@m
 return all_matrices,tip_positions

clips={'reload':('PKM_Reload_Normal',6.5),'reload_empty':('PKM_Reload_Empty',7.5)}
record={}
for key,(name,duration) in clips.items():
 original=bpy.data.actions[name];action(original);samples=[]
 for f in range(round(duration*60)+1):
  s.frame_set(f);bpy.context.view_layer.update();samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
 new=bpy.data.actions.new(name+'_HandReload10');new.use_fake_user=True;r.animation_data.action=new;previous={};solvers={p:BeltDynamics(lengths[:end]) for p in ['', 'New_']}
 for f,old in enumerate(samples):
  t=f/60;W=old['WPN_root']@fit;d={n:m.copy() for n,m in old.items()};empty=key=='reload_empty'
  boxes={'':T(off*ramp(t,2.60,3.15))@around(pivot,rot('Y',-20*ramp(t,2.60,3.15))),
         'New_':T(off*(1-ramp(t,3.65,4.35)))@around(pivot,rot('Y',-20*(1-ramp(t,3.65,4.35))))}
  for prefix,box in boxes.items():
   for part in ['PKM_Box','PKM_BoxLid','PKM_BeltRoot']:d[prefix+part]=W@box@Bi@rest[prefix+part]
  belt_matrices,chain=belts(t,W,boxes,solvers);d.update(belt_matrices)
  cover=cover_matrix(t);left_cover=hand_contact('l',(.028,.275,.112),(-1,0,0),(0,0,-1),'cover')
  # Open the latch and drive the lid; release before the far end leaves reach.
  L={'ready':ready_hand('l'),
     'approach':hand_contact('l',(.095,.265,.14),(-1,0,-.08),(0,0,-1),'open'),
     'cover':transform_hand(left_cover,cover),
     'release':transform_hand(hand_contact('l',(.050,.26,.132),(-1,0,0),(0,0,-1),'open'),cover_matrix(.94)),
     'hover':hand_contact('l',(.07,.06,.17),(-1,-.06,0),(0,0,-1),'open'),
     'belt':hand_contact('l',(Vector((0,.038,.09)) if empty else chain[''])+Vector((0,0,.002)),(-1,0,0),(0,0,-1),'pinch' if not empty else 'press'),
     'clear':hand_contact('l',(.11,.04,.125),(-.8,-.3,-.15),(0,0,-1),'open')}
  left=hand_seq(t,[(0,'ready'),(.28,'ready'),(.50,'approach'),(.65,'cover'),(.94,'cover'),(1.06,'release'),(1.29,'hover'),(1.43,'belt'),(1.90,'belt'),(2.13,'clear'),(2.30,'ready'),(duration,'ready')],L)
  Rg=hand_contact('r',(-.124,.041,-.098),(0,-.10,-1),(1,0,0),'box')
  right_cover=hand_contact('r',(-.009,.178,.115),(1,0,0),(0,0,-1),'press')
  Rtargets={'ready':ready_hand('r'),
     'box_hover':hand_contact('r',(-.20,.09,-.055),(0,-.1,-1),(1,0,0),'open'),
     'old_box':transform_hand(Rg,boxes['']),
     'away':hand_contact('r',(-.30,.34,-.29),(0,-.18,-1),(1,0,0),'open'),
     'new_box':transform_hand(Rg,boxes['New_']),
     'box_release':hand_contact('r',(-.18,.09,-.035),(0,-.08,-1),(1,0,0),'open'),
     'belt_hover':hand_contact('r',(-.15,.08,.12),(1,0,0),(0,0,-1),'open'),
     'belt':hand_contact('r',chain['New_']+Vector((0,0,.003)),(1,0,0),(0,0,-1),'pinch'),
     'belt_release':hand_contact('r',(-.065,.04,.155),(1,0,0),(0,0,-1),'open'),
     'cover':transform_hand(right_cover,cover),
     'cover_away':hand_contact('r',(-.145,.22,.14),(1,-.25,-.1),(0,0,-1),'open')}
  charge=old['PKM_Charge'];charge_delta=W.inverted()@charge@rest['PKM_Charge'].inverted()@B
  Rtargets['charge']=transform_hand(hand_contact('r',(-.055,.116,.023),(.05,-1,0),(0,0,-1),'charge'),charge_delta)
  Rtargets['charge_hover']=hand_contact('r',(-.115,.15,.055),(.05,-1,0),(0,0,-1),'open')
  keys=[(0,'ready'),(2.30,'ready'),(2.45,'box_hover'),(2.60,'old_box'),(2.95,'old_box'),(3.23,'away'),(3.72,'away'),(4.00,'new_box'),(4.35,'new_box'),(4.46,'box_release'),(4.58,'belt_hover'),(4.70,'belt'),(5.10,'belt'),(5.18,'belt_release'),(5.25,'cover'),(5.72,'cover'),(5.90,'cover_away')]
  if empty:keys += [(5.97,'charge_hover'),(6.03,'charge'),(6.42,'charge'),(6.48,'charge_hover'),(6.70,'cover_away'),(7.16,'ready'),(7.50,'ready')]
  else:keys += [(6.30,'ready'),(6.50,'ready')]
  right=hand_seq(t,keys,Rtargets)
  active_l=ramp(t,.26,.55)*(1-ramp(t,2.13,2.30))
  active_r=ramp(t,2.30,2.52)*(1-ramp(t,6.68 if empty else 5.90,7.16 if empty else 6.30))
  d.update(arm_pose('l',left,W,t,active_l));d.update(arm_pose('r',right,W,t,active_r))
  # All arm tracks start and end at the exact current idle assembly. The
  # weapon and its mechanical cues keep the existing source-time contract.
  for n,m in d.items():
   p=parent[n];pose=d[p].inverted()@m if p else m;loc,q,scale=(localrest[n].inverted()@pose).decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();bone=r.pose.bones[n];bone.location=loc;bone.rotation_mode='QUATERNION';bone.rotation_quaternion=q;bone.scale=(1,1,1)
   for prop in ['location','rotation_quaternion','scale']:bone.keyframe_insert(prop,frame=f,group=n)
 for layer in new.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for point in curve.keyframe_points:point.interpolation='LINEAR'
 s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(E/('A_PKM_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1)
 record[key]={'action':new.name,'seconds':duration,'fps':60,'frames':s.frame_end+1};print('PKM10_AUTHORED',key,flush=True)
action(bpy.data.actions['PKM_Reload_Normal_HandReload10']);s.frame_start=0;s.frame_end=390;s.frame_set(0)
s.timeline_markers.clear()
for label,t in [('L_Latch',.65),('L_ReleaseCover',.94),('L_PinchBelt',1.43),('L_LiftBelt',1.65),('L_ReturnSupport',2.3),('R_BoxGrip',2.6),('R_NewBoxSeat',4.35),('R_PinchChain',4.7),('R_ChainSeat',5.1),('R_PalmCover',5.25),('R_CoverLatch',5.72)]:s.timeline_markers.new(label,frame=round(t*60))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_ReloadHands_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':{k:v[1] for k,v in clips.items()},'actions':record,'source':'Belt08','surface_contract':'SectionFix09','reference':str(R/'References/PKM_UserReloadReference.mp4'),'mesh_changed':False,'skeleton_changed':False,'weights_changed':False,'new_preview_rendered':False,'runtime_tested':False,'adaptation':'Object-local contact; phase-specific anatomical finger shapes; whole-forearm orientation; supported left/right handoff; box and chain contact paths fitted to this model'},indent=2))
print('PKM10_RELOAD_HANDS_COMPLETE',flush=True)
