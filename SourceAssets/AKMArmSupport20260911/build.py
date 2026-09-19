"""M4 wrist-natural two-bone support method, measured for AKM; preserve hand trajectories."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;variant=sys.argv[sys.argv.index('--')+1];out=O/variant;out.mkdir(exist_ok=True)
probe=json.loads((O/'probe.json').read_text());offset=Vector(probe[variant]['shoulder_delta'])*(.70 if variant=='angled' else 0)
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def weight(clip,f):
 if 'reload' not in clip:return 1
 start=380 if 'empty' in clip else 270
 return 1-smooth((f-18)/24)+smooth((f-start)/60)
report={}
for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty']:
 base=O.parent/('AKMGripReturn20260911/Final' if 'reload' in clip else 'AKMAttachments20260911')
 source=base/variant/f'A_AKM_{variant}_{clip}.blend';bpy.ops.wm.open_mainfile(filepath=str(source))
 r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;end=s.frame_end
 names=[b.name for b in r.pose.bones];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 samples=[]
 for f in range(end+1):
  s.frame_set(f);samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
 r.animation_data.action=None;output=[];metric=None
 for f,old in enumerate(samples):
  p={n:m.copy() for n,m in old.items()};w=weight(clip,f)
  if w>0:
   un,fn,hn='upperarm_l','lowerarm_l','hand_l';H=old[hn];A=old[un].translation+offset*w;target=H.translation
   l1=(old[fn].translation-old[un].translation).length;l2=(target-old[fn].translation).length
   axis=(target-A).normalized();extra=axis*max(0,(target-A).length-(l1+l2-.005));A+=extra
   p['clavicle_l'].translation+=offset*w+extra
   dist=(target-A).length;axis=(target-A).normalized();pole=old[fn].translation-A;pole-=axis*pole.dot(axis)
   desired=H.to_3x3()@rest[hn].to_3x3().inverted()@(rest[hn].translation-rest[fn].translation).normalized()
   natural=target-desired*l2-A;natural-=axis*natural.dot(axis);pole=pole.normalized().lerp(natural.normalized(),w).normalized()
   along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
   u=(E-A).normalized();v=(target-E).normalized();ou=(old[fn].translation-old[un].translation).normalized();ov=(target-old[fn].translation).normalized()
   p[un]=Matrix.LocRotScale(A,ou.rotation_difference(u)@old[un].to_quaternion(),old[un].to_scale())
   p[fn]=Matrix.LocRotScale(E,ov.rotation_difference(v)@old[fn].to_quaternion(),old[fn].to_scale())
   for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:p[n]=p[un]@old[un].inverted()@old[n]
   neutral=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion();q=H.to_quaternion()@neutral.inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
   for n,t in [('lowerarm_twist_02_l',.55),('lowerarm_twist_01_l',.95)]:
    m=p[fn]@rest[fn].inverted()@rest[n];naturalq=Quaternion(v,twist*t)@m.to_quaternion();oldq=(p[fn]@old[fn].inverted()@old[n]).to_quaternion()
    p[n]=Matrix.LocRotScale(m.translation,oldq.slerp(naturalq,w),old[n].to_scale())
   if f==0:metric={'wrist_bend_before':math.degrees(ov.angle(desired)),'wrist_bend_after':math.degrees(v.angle(desired)),'elbow_before':math.degrees(ou.angle(ov)),'elbow_after':math.degrees(u.angle(v)),'shoulder_offset_m':list(offset),'hand_target_unchanged':True}
  output.append({n:lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]) for n in names})
 a=bpy.data.actions.new(f'A_AKM_{variant}_{clip}');a.use_fake_user=True;r.animation_data.action=a;previous={}
 for f,pose in enumerate(output):
  for n,m in pose.items():
   loc,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 # Verify the actual evaluated chain, digit contact and non-target bones against accepted source.
 maxhand=maxfinger=maxright=maxlen=maxscale=0
 for f,old in enumerate(samples):
  s.frame_set(f);p={b.name:b.matrix.copy() for b in r.pose.bones}
  for n in names:
   err=(p[n].translation-old[n].translation).length
   if n=='hand_l':maxhand=max(maxhand,err);assert p[n].to_quaternion().rotation_difference(old[n].to_quaternion()).angle<.002
   elif n.startswith(('index','middle','ring','pinky','thumb')) and n.endswith('_l'):maxfinger=max(maxfinger,err)
   elif n.endswith('_r') or n.startswith('WPN'):maxright=max(maxright,err)
   maxscale=max(maxscale,(r.pose.bones[n].scale-output[f][n].to_scale()).length)
  for n,parent in [('lowerarm_l','upperarm_l'),('hand_l','lowerarm_l')]:maxlen=max(maxlen,abs((p[n].translation-p[parent].translation).length-(old[n].translation-old[parent].translation).length))
 assert max(maxhand,maxfinger,maxright,maxlen)<.00002,(clip,maxhand,maxfinger,maxright,maxlen)
 s.render.fps=120;s.frame_set(end);name=f'A_AKM_{variant}_{clip}'
 bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[clip]={'source':str(source),'frames':end,'duration':end/120,'metrics':metric,'max_hand_error_m':maxhand,'max_digit_error_m':maxfinger,'max_preserved_error_m':maxright,'max_length_error_m':maxlen}
 (out/'validation.json').write_text(json.dumps(report,indent=2));print('AKM_SUPPORT_CLIP_PASS',variant,clip,flush=True)
print('AKM_SUPPORT_BUILD_PASS',variant,flush=True)
