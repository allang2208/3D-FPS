"""QBZ191 O: original rear-grip contact, supported wrist, same 0.9 s clock."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).parent;S=P.parent
sys.path[:0]=[str(P),str(S/'M4QuickMeleeRefine20260919K'),str(S/'M4QuickMeleeRefine20260919N')]
from grip_solver import GripBearing
from arm_support import ArmSupport
from natural_wrist import NaturalWrist,smooth
class LockedWrist(NaturalWrist):
 def target(self,pose,angle):return pose['hand_r'].copy()
manifest=json.loads((S/'RifleQuickMelee20260919/authoring.json').read_text())
spec=manifest['weapons']['QBZ191'];report={'duration':.9,'contact':1/6,'weapons':{'QBZ191':{'mesh':spec['mesh'],'profiles':{}}}}
bpy.context.preferences.filepaths.save_version=0
for profile,item in spec['profiles'].items():
 bpy.ops.wm.open_mainfile(filepath=item['blend'])
 rig=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
 old=[]
 for f in range(109):
  scene.frame_set(f);bpy.context.view_layer.update();old.append({b.name:b.matrix.copy() for b in rig.pose.bones})
 idle=old[0];rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
 names=list(rest);parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
 lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 scene.frame_set(0);bpy.context.view_layer.update()
 support=ArmSupport(rig,idle);natural=LockedWrist(idle,rest,support.stations)
 stock=Vector(spec['stock_author_m']);bearing=GripBearing(idle,rest,stock)
 adjustments=[]
 for f,p in enumerate(old):
  t=f/120;w=smooth(t/.1)*(1-smooth((t-.72)/.146666667))
  if w<1e-7:adjustments.append([0.]*6);continue
  gun,info=bearing.fit(p['WPN_root'],{s:p['upperarm_'+s].translation for s in ('r','l')},w)
  adjustments.append(list(bearing.previous)+list(bearing.translation))
 # Remove search quantization while keeping one continuous entry/contact/return.
 for _ in range(3):
  adjustments=[[sum(adjustments[min(108,max(0,f+k-2))][j]*weight for k,weight in enumerate((1,4,6,4,1)))/16
                for j in range(6)] for f in range(109)]
 def mix(a,b,w):
  al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
  return Matrix.LocRotScale(al.lerp(bl,w),aq.slerp(bq,w),asc.lerp(bsc,w))
 rows=[];previous={};metrics=[];sample_frames=[i/4 for i in range(433)]
 for f in sample_frames:
  lo=int(f);hi=min(108,lo+1);fraction=f-lo
  p={n:mix(old[lo][n],old[hi][n],fraction) for n in names}
  pose={n:m.copy() for n,m in idle.items()};t=f/120;w=smooth(t/.1)*(1-smooth((t-.72)/.146666667))
  if 0<f<104:
   values=[a*(1-fraction)+b*fraction for a,b in zip(adjustments[lo],adjustments[hi])]
   v=Vector(values[:3]);shift=Vector(values[3:])
   cap=math.radians(100)*w
   if v.length>cap:v=v.normalized()*cap
   if shift.length>.16*w:shift=shift.normalized()*.16*w
   q=Quaternion(v.normalized(),v.length) if v.length>1e-8 else Quaternion()
   pivot=(p['WPN_root']@bearing.hands['r']).translation
   gun=Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)@p['WPN_root'];gun.translation+=shift
   delta=gun@idle['WPN_root'].inverted()
   # Reach projection also carries the complete gun/hand group.
   delta=support.fit_group(delta,w)
   for n in names:
    if n.startswith('WPN_'):pose[n]=delta@idle[n]
   for side in ('r','l'):support.apply(pose,side,delta@idle['hand_'+side],w)
   pose.update(natural.apply(pose,t))
   # LockedWrist changes only arm support: hand and every descendant remain
   # exactly the gun-carried idle grip, including local finger transforms.
  row={}
  for n in names:
   b=lr[n].inverted()@(pose[parents[n]].inverted()@pose[n] if parents[n] else pose[n])
   loc,q,sc=b.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();row[n]=(loc,q,sc)
  rows.append(row)
  delta=pose['WPN_root']@p['WPN_root'].inverted()
  metrics.append({'frame':f,'stock_delta_cm':list(100*((pose['WPN_root']@stock)-(p['WPN_root']@stock))),
                  'group_rotation_deg':math.degrees(delta.to_quaternion().angle)})
 action=bpy.data.actions.new(f'QBZ191_QuickCombat_O_{profile}');action.use_fake_user=True;rig.animation_data.action=action
 for n in names:
  b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
  for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
 bag=action.layers[0].strips[0].channelbag(action.slots[0]);curves={(c.data_path,c.array_index):c for c in bag.fcurves}
 for n in names:
  for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(rows))
    c.keyframe_points.foreach_set('co',[v for f,row in zip(sample_frames,rows) for v in (f,row[n][field][axis])])
    for key in c.keyframe_points:key.interpolation='LINEAR'
    c.update()
 rig.animation_data.action_slot=action.slots[0];scene.render.fps=120;scene.render.fps_base=1
 scene.frame_start=0;scene.frame_end=108;scene.frame_set(0)
 dest=P/profile;(dest/'Animations').mkdir(parents=True,exist_ok=True)
 name=f'A_QBZ191_QuickCombat_{profile}';fbx=dest/'Animations'/f'{name}.fbx'
 bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
  add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
  bake_anim_force_startend_keying=True,bake_anim_step=.25,bake_anim_simplify_factor=0)
 blend=dest/f'QBZ191_QuickCombat_{profile}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
 report['weapons']['QBZ191']['profiles'][profile]={'source':item['blend'],'source_action':item['action'],'action':action.name,
  'blend':str(blend),'fbx':str(fbx),'sample_rate':480,'asset':item['asset'],'motion_changes':metrics,'wrist':natural.records}
 (P/'authoring.json').write_text(json.dumps(report,indent=2));print('QBZ_O_EXPORTED',profile,flush=True)
