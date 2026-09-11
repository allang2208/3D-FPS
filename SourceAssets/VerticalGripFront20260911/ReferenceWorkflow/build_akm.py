import bpy,json,math,sys,runpy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(O))
from audit_m4 import support,smooth
variant=sys.argv[sys.argv.index('--')+1];requested=sys.argv[sys.argv.index('--')+2:];D=O/'akm'/variant;D.mkdir(exist_ok=True)
fit=json.loads((O/'akm/fits.json').read_text())[variant];Glocal=Matrix(fit['grip_in_root']);Glocal=Matrix.LocRotScale(Glocal.translation,Glocal.to_quaternion(),Vector((1,1,1)));sourcepath=Path(fit['source']);m4fit=json.loads(Path(fit['source_fit']).read_text());title=sourcepath.stem.removeprefix('A_M4_').removesuffix('_idle')
# Extract the accepted M4 surface-safe opening in mount space. Only its grasp/release is retargeted.
bpy.ops.wm.open_mainfile(filepath=str(sourcepath.with_name(f'A_M4_{title}_reload.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;release=[]
for k in range(73):
 f=k/8;s.frame_set(int(f),subframe=f%1);mg=Matrix(m4fit['grip_in_root']);mg=Matrix.LocRotScale(mg.translation,mg.to_quaternion(),Vector((1,1,1)));G=r.pose.bones['WPN_root'].matrix@mg;H=r.pose.bones['hand_l'].matrix
 release.append({'hand':[list(x) for x in G.inverted()@H],'digits':{b.name:list(b.matrix_basis.to_quaternion()) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))}})
(D/'release.json').write_text(json.dumps(release,indent=2))
def opening(u):
 t=max(0,min(1,u))*72;i=min(int(t),71);a=t-i;lo,hi=release[i],release[i+1];L,Q,Z=Matrix(lo['hand']).decompose();l,q,z=Matrix(hi['hand']).decompose()
 return Matrix.LocRotScale(L.lerp(l,a),Q.slerp(q,a),Z),{n:Quaternion(lo['digits'][n]).slerp(Quaternion(hi['digits'][n]),a) for n in lo['digits']}
def arm(p,rest,H,w,delta):
 old={n:m.copy() for n,m in p.items()};un,fn,hn='upperarm_l','lowerarm_l','hand_l';A=old[un].translation+delta*w;T=H.translation;l1=(old[fn].translation-old[un].translation).length;l2=(old[hn].translation-old[fn].translation).length
 axis=(T-A).normalized();dist=(T-A).length;shift=axis*max(0,dist-(l1+l2-.005));A+=shift;dist=(T-A).length;axis=(T-A).normalized();p['clavicle_l'].translation+=delta*w+shift
 desired=H.to_3x3()@rest[hn].to_3x3().inverted()@(rest[hn].translation-rest[fn].translation).normalized();pole=old[fn].translation-A;pole-=axis*pole.dot(axis);natural=T-desired*l2-A;natural-=axis*natural.dot(axis);pole=pole.normalized().lerp(natural.normalized(),w).normalized()
 along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));u=(E-A).normalized();v=(T-E).normalized();ou=(old[fn].translation-old[un].translation).normalized();ov=(old[hn].translation-old[fn].translation).normalized()
 p[un]=Matrix.LocRotScale(A,ou.rotation_difference(u)@old[un].to_quaternion(),old[un].to_scale());p[fn]=Matrix.LocRotScale(E,ov.rotation_difference(v)@old[fn].to_quaternion(),old[fn].to_scale())
 for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:p[n]=p[un]@old[un].inverted()@old[n]
 for n in ['lowerarm_twist_01_l','lowerarm_twist_02_l']:p[n]=p[fn]@old[fn].inverted()@old[n]
 p[hn]=H;support(p,rest,w)
 return {'wrist_axis_bend_deg':math.degrees(v.angle(desired)),'elbow_bend_deg':math.degrees(u.angle(v)),'shoulder_delta_m':list(delta)}
def render(r,G,label):
 s=bpy.context.scene
 for ob in s.objects:
  if ob.type=='LIGHT':ob.hide_render=True
 cam=bpy.data.cameras.new('Audit');c=bpy.data.objects.new('Audit',cam);s.collection.objects.link(c);s.camera=c;cam.type='ORTHO';cam.clip_start=.001
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100
 for offset in [(-.6,-.4,.8),(.6,.4,.7)]:
  ld=bpy.data.lights.new('Audit','AREA');ld.energy=85;ld.size=1;l=bpy.data.objects.new('Audit',ld);s.collection.objects.link(l);l.location=G.translation+Vector(offset);l.rotation_euler=(G.translation-l.location).to_track_quat('-Z','Y').to_euler()
 Gn=G.to_quaternion().to_matrix()
 for view,center,offset,scale in [('arm',(-.15,0,-.10),(0,-.8,.22),.70),('palm',(0,0,-.035),(0,-.4,.01),.28),('front',(0,0,-.035),(.4,0,.01),.28)]:
  focus=G.translation+Gn@Vector(center);c.location=focus+Gn@Vector(offset);c.rotation_euler=(focus-c.location).to_track_quat('-Z','Y').to_euler();cam.ortho_scale=scale;s.render.filepath=str(D/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
report=json.loads((D/'build.json').read_text()) if (D/'build.json').exists() else {}
for clip,end in [('idle',5),('aim',5),('fire',12),('aim_fire',12),('equip',204),('reload',400),('reload_empty',515),('drum_reload',400),('drum_reload_empty',515)]:
 if requested and clip not in requested:continue
 source=S/'AKMReloadPolish20260911/base'/f'A_AKM_{clip}.blend' if 'reload' in clip else S/'AKMAttachments20260911/AKM_Attachments_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 if 'reload' not in clip:
  a=bpy.data.actions['AKM_EquipCharge' if clip=='equip' else 'AKM_Native_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 names=[b.name for b in r.pose.bones];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 samples=[]
 for f in range(end+1):s.frame_set(f);samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
 old=samples[0];H=old['WPN_root']@Glocal@opening(0)[0];A=old['upperarm_l'].translation;l1=(old['lowerarm_l'].translation-A).length;l2=(old['hand_l'].translation-old['lowerarm_l'].translation).length
 desired=H.to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized();E=H.translation-desired*l2;delta=(E+(A-E).normalized()*l1-A)*.70
 r.animation_data.action=None;output=[];metric={}
 for f,old in enumerate(samples):
  p={n:m.copy() for n,m in old.items()};u=0;w=1
  if 'reload' in clip:
   start=380 if 'empty' in clip else 270;finish=start+60;w=1-smooth((f-18)/24)+smooth((f-start)/40);u=max(0,min(1,f/18)) if f<end/2 else 1-max(0,min(1,(f-(finish-24))/24))
  original={n:lr[n].inverted()@(old[parents[n]].inverted()@old[n] if parents[n] else old[n]) for n in names}
  if w>0:
   h,digits=opening(u);H=old['WPN_root']@Glocal@h
   l,q,z=old['hand_l'].decompose();L,Q,Z=H.decompose();H=Matrix.LocRotScale(l.lerp(L,w),q.slerp(Q,w),z)
   if variant in ['vertical','angled','canted'] and w<1:H.translation+=(old['WPN_root']@Glocal).to_3x3()@Vector((-.02,.15,-.085) if variant=='angled' else (-.02,.13,-.07))*math.sin(math.pi*w)
   metric0=arm(p,rest,H,w,delta)
   if f==0:metric=metric0
   for n,q in digits.items():
    l,oldq,z=original[n].decompose();p[n]=p[parents[n]]@lr[n]@Matrix.LocRotScale(l,oldq.slerp(q,w),z)
  basis={}
  for n in names:
   local=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);l,q,z=original[n].decompose()
   basis[n]=Matrix.LocRotScale(local.translation if n=='clavicle_l' else l,local.to_quaternion(),z)
  output.append(basis)
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
 maxnonleft=maxcontact=maxlocal=maxscale=0
 for f,old in enumerate(samples):
  s.frame_set(f)
  for b in r.pose.bones:
   n=b.name;err=(b.matrix.translation-old[n].translation).length;orig=lr[n].inverted()@(old[parents[n]].inverted()@old[n] if parents[n] else old[n]);maxscale=max(maxscale,(b.matrix_basis.to_scale()-orig.to_scale()).length)
   if not n.endswith('_l'):maxnonleft=max(maxnonleft,err)
   if n!='clavicle_l':maxlocal=max(maxlocal,(b.matrix_basis.translation-orig.translation).length)
   if 'reload' in clip and 42<=f<=(380 if 'empty' in clip else 270):maxcontact=max(maxcontact,err)
 assert max(maxnonleft,maxcontact,maxlocal,maxscale)<.00003,(clip,maxnonleft,maxcontact,maxlocal,maxscale)
 s.render.fps=120;s.frame_start=0;s.frame_end=end;s.frame_set(0);runpy.run_path(str(O/'ReferenceWorkflow/akm_preview_visibility.py'))['configure_preview'](clip.startswith('drum'),variant)
 if variant in ['vertical','canted','angled']:
  existing=bpy.data.objects.get(f'SM_AKM_{variant}')
  if existing:bpy.data.objects.remove(existing,do_unlink=True)
  with bpy.data.libraries.load(str(O/'akm'/f'SM_AKM_{variant}.blend'),link=False) as (src,dst):dst.objects=[f'SM_AKM_{variant}']
  ob=dst.objects[0];s.collection.objects.link(ob);ob.matrix_world=r.matrix_world@r.pose.bones['WPN_root'].matrix;world=ob.matrix_world.copy();ob.parent=r;ob.parent_type='BONE';ob.parent_bone='WPN_root';bpy.context.view_layer.update();ob.matrix_world=world
 name=f'A_AKM_{variant}_{clip}';bpy.ops.wm.save_as_mainfile(filepath=str(D/(name+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[clip]={'source':str(source),'duration':end/120,'frames':end,'sample_rate':120,'arm':metric,'nonleft_error_m':maxnonleft,'preserved_contact_error_m':maxcontact,'local_translation_error_m':maxlocal,'scale_error':maxscale}
 (D/'build.json').write_text(json.dumps(report,indent=2));print('AKM_GRIP_BUILD_PASS',variant,clip,metric,flush=True)
 if clip=='idle':render(r,r.pose.bones['WPN_root'].matrix@Glocal,'idle')
