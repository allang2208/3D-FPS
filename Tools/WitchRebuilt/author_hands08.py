"""Anatomical left/right palm grasps; no arm, cloth or body re-authoring."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Revision08'
ROLES=('Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight','ThrowPoisonBottle','DeathBackward')
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def world(r,n):return r.matrix_world@r.pose.bones[n].matrix

# Use the retained staff geometry for its local shaft radius at the grip.
staffpath=ROOT.parent/'WitchMeshy20260919/Authoring/LayeredV04/Preserved/Staff.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(staffpath),use_anim=False)
staffpoints=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
shaft=[];shaft_ellipse=[]
for j in range(13):
 z=.86+j*.01;values=sorted(p.xy.length for p in staffpoints if abs(p.z-z)<.012)
 shaft.append((z,values[int(.85*(len(values)-1))] if values else .035))
 band=[p for p in staffpoints if abs(p.z-z)<.012]
 shaft_ellipse.append((z,max(abs(p.x) for p in band) if band else .045,max(abs(p.y) for p in band) if band else .033))
bottle=[(.02,.047),(.10,.0474),(.12,.0428),(.13,.0324),(.14,.0163),(.15,.0171),(.16,.023),(.18,.016)]
def radius(z,profile):
 for (a,ra),(b,rb) in zip(profile,profile[1:]):
  if a<=z<=b:return ra+(rb-ra)*(z-a)/(b-a)
 return profile[0][1] if z<profile[0][0] else profile[-1][1]

bpy.ops.wm.open_mainfile(filepath=str(OUT/'Before/Authoring/WitchRebuilt_Idle.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');r.animation_data_clear()
for pb in r.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones};closed={};reports={}
for side in ('l','r'):
 hand=rest['hand_'+side];along=(rest['middle_01_'+side].translation-hand.translation).normalized()
 across=(rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
 palm=along.cross(across).normalized()*(1 if side=='l' else -1)
 center=hand.translation+along*.085+palm*(.050 if side=='l' else .067)
 height=.92 if side=='l' else .118;profile=shaft if side=='l' else bottle;sign=-1 if side=='l' else 1
 radial_along=(along-across*along.dot(across)).normalized()
 def contact_radius(z,direction):
  if side=='r':return radius(z,bottle)
  rx=radius(z,[(z,x) for z,x,y in shaft_ellipse]);ry=radius(z,[(z,y) for z,x,y in shaft_ellipse])
  a=direction.dot(radial_along);p=direction.dot(palm)
  return 1/math.sqrt((a/rx)**2+(p/ry)**2) if a*a+p*p>1e-8 else min(rx,ry)
 reports[side]={'palm_cross_sign':1 if side=='l' else -1,'grip_height_m':height,'profile':profile,'fingers':{}}
 for finger in ('index','middle','ring','pinky','thumb'):
  names=[f'{finger}_{j:02d}_{side}' for j in (1,2,3)]
  parent=rest[r.data.bones[names[0]].parent.name]
  local=[r.data.bones[n].parent.matrix_local.inverted()@r.data.bones[n].matrix_local for n in names]
  initial=[rest[n] for n in names]
  tipworld=initial[2].translation+(initial[2].translation-initial[1].translation)*.80
  tiplocal=initial[2].inverted()@tipworld
  thumb_axes=[]
  for j in range(3):
   direction=((initial[j+1].translation if j<2 else tipworld)-initial[j].translation).normalized()
   thumb_axes.append(initial[j].to_quaternion().inverted()@direction.cross(palm).normalized())
  def evaluate(angles):
   previous=parent;matrices=[]
   for j in range(3):
    m=previous@local[j];position=m.translation.copy()
    if j==0:
     q=Quaternion(along if finger=='thumb' else palm,math.radians(angles[3]));m=q.to_matrix().to_4x4()@m;m.translation=position
     if finger=='thumb':
      q=Quaternion(palm,math.radians(angles[4]));m=q.to_matrix().to_4x4()@m;m.translation=position
    # Thumb hinges follow the opposed metacarpal. A shared global finger axis
    # gives the thumb a sideways roll instead of flexion after CMC opposition.
    axis=m.to_quaternion()@thumb_axes[j] if finger=='thumb' else across
    q=Quaternion(axis,math.radians(angles[j] if finger=='thumb' else sign*angles[j]));m=q.to_matrix().to_4x4()@m;m.translation=position
    matrices.append(m);previous=m
   return matrices,matrices[-1]@tiplocal
  def cost(angles):
   mats,tip=evaluate(angles);points=[m.translation for m in mats]+[tip]
   tip_v=tip-center;tip_z=height+tip_v.dot(across);tip_radial=tip_v-across*tip_v.dot(across)
   gap=tip_radial.length-contact_radius(tip_z,tip_radial.normalized())-.005
   # Surface contact is free to slide around the section. A single imposed
   # far-side point makes short fingers reverse or straighten against the shaft.
   value=gap*gap*20
   if finger=='thumb':
    # The thumb opposes the fingers from the wrist side, but may contact higher
    # on the shaft/shoulder. Fixing its axial contact to the palm center forces
    # a backwards CMC fold on this long, splayed reference thumb.
    value+=max(0,tip_radial.dot(radial_along)+.006)**2*10
    value+=(tip_v.dot(across)-.037)**2*2
    value+=sum(((angles[j]-v)/90)**2 for j,v in enumerate((25,35,20,0,0)))*.00008
   else:
    value+=max(0,-tip_radial.dot(radial_along)-.012)**2*3
    value+=max(0,-tip_radial.dot(palm)-.008)**2*8
    value+=sum(((angles[j]-v)/90)**2 for j,v in enumerate((28,60,35)))*.00012
   for a,b in zip(points,points[1:]):
    for t in (.25,.5,.75,1.):
     p=a.lerp(b,t);v=p-center;z=height+v.dot(across)
     if (side=='l' or .012<z<.181):
      radial=(v-across*v.dot(across)).length
      direction=(v-across*v.dot(across)).normalized()
      value+=max(0,contact_radius(z,direction)+.004-radial)**2*20
   value+=((angles[2]-.65*angles[1])/100)**2*(.00012 if finger=='thumb' else .0006)
   if finger!='thumb':value+=((angles[0]-40)/100)**2*.00015
   return value
  bounds=[(0,80),(0,100),(0,72),(-10,10)] if finger!='thumb' else [(0,80),(0,80),(0,65),(-65,65),(-65,65)]
  if finger=='pinky':bounds[3]=(-35,35)
  elif finger=='ring':bounds[3]=(-18,18)
  best=None
  seeds=[[start,start,start*.6,0]+([0] if finger=='thumb' else []) for start in (15,35,55)]
  if finger=='thumb':seeds.extend([[20,35,20,a,b] for a in (-55,55) for b in (-40,40)])
  for seed in seeds:
   angles=seed[:];score=cost(angles)
   for step in (20,10,5,2,1,.4):
    for iteration in range(12):
     improved=False
     for j in range(len(angles)):
      for direction in (-1,1):
       trial=angles[:];trial[j]=max(bounds[j][0],min(bounds[j][1],trial[j]+direction*step));c=cost(trial)
       if c<score:angles,score=trial,c;improved=True
     if not improved:break
   if best is None or score<best[0]:best=score,angles
  matrices,tip=evaluate(best[1]);previous=parent
  for n,lr,m in zip(names,local,matrices):
   q=(lr.inverted()@previous.inverted()@m).to_quaternion().normalized();closed[n]=list(q);previous=m
  def coords(p):return [round((p-hand.translation).dot(v)*100,3) for v in (radial_along,across,palm)]
  v=tip-center;radial=v-across*v.dot(across);gap=radial.length-contact_radius(height+v.dot(across),radial.normalized())
  reports[side]['fingers'][finger]={'authored_angles_degrees':best[1],
   'tip_surface_gap_cm':gap*100,'tip_hand_axes_cm':coords(tip),'joints_hand_axes_cm':[coords(m.translation) for m in matrices]}

(OUT/'hands_authoring.json').write_text(json.dumps({'grips':reports,'closed_quaternions':closed,'changed_tracks':'30 finger joints only; body, hand/wrist, elbows, cloth and scale retained','throw_release_seconds':.75},indent=2))
if '--solve-only' in sys.argv:
 print('Hands08 grip pose authored; FBX export deferred.');sys.exit(0)

for role in ROLES:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/f'Before/Authoring/WitchRebuilt_{role}.blend'))
 scene=bpy.context.scene;r=next(o for o in scene.objects if o.type=='ARMATURE');last={}
 for f in range(scene.frame_start,scene.frame_end+1):
  scene.frame_set(f);t=(f-scene.frame_start)/scene.render.fps
  for side in ('l','r'):
   for finger,delay,amount in [('thumb',-.018,.72),('index',-.008,.92),('middle',0,.90),('ring',.014,.82),('pinky',.024,.75)]:
    opening=ramp(t,.724+delay,.790+delay)*(1-ramp(t,1.10+delay,1.47+delay))*amount if side=='r' and role=='ThrowPoisonBottle' else 0.
    for j in (1,2,3):
     name=f'{finger}_{j:02d}_{side}';pb=r.pose.bones[name];pb.rotation_mode='QUATERNION'
     q=Quaternion(closed[name]).slerp(Quaternion(),opening)
     if name in last and q.dot(last[name])<0:q.negate()
     last[name]=q;pb.rotation_quaternion=q;pb.keyframe_insert('rotation_quaternion',frame=f)
  bpy.context.view_layer.update()
 r['grip_revision']='Hands08: anatomical opposing palms, shaft/shoulder finger fit';scene.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'Authoring/WitchRebuilt_{role}.blend'))
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(ROOT/f'Delivery/A_WitchRebuilt_{role}.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
  use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
  bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,
  axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
 print('AUTHORED Hands08 '+role,flush=True)
manifest_path=ROOT/'Authoring/motion_manifest.json';manifest=json.loads((OUT/'Before/Authoring/motion_manifest.json').read_text(encoding='utf-8'))
for role in ROLES:manifest[role]['grip_revision']='Hands08: mirrored anatomical palm flexion and independent thumb opposition'
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'hands_authoring.json').write_text(json.dumps({'grips':reports,'closed_quaternions':closed,'changed_tracks':'30 finger joints only; body, hand/wrist, elbows, cloth and scale retained','throw_release_seconds':.75},indent=2))
print('Hands08 source and eight animation FBXs saved; no gameplay or render run.')
