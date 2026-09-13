"""Reuse M4 handling rhythm while retaining QBZ magazine/side-handle contacts."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'VREGripExtensions20260912/ReferenceWorkflow'))
from front_pose import solve_arm
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'QBZ191_Attachments_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;r.data.pose_position='POSE'
ref=json.loads((O/'m4_reference_motion.json').read_text());inputs=json.loads((O/'geometry_inputs.json').read_text());models=json.loads((O/'models.json').read_text())
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest);parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
finger=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
def smooth(t):t=max(0,min(1,t));return t*t*t*(10+t*(-15+6*t))
def mix(a,b,t):return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),a.to_scale().lerp(b.to_scale(),t))
def shift(m,v):m=m.copy();m.translation+=Vector(v);return m
def track(keys,f):
 if f<=keys[0][0]:return keys[0][1].copy()
 for (a,A),(b,B) in zip(keys,keys[1:]):
  if f<=b:return mix(A,B,smooth((f-a)/(b-a)))
 return keys[-1][1].copy()
def pose(a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
def basis(p,n):return lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n])
def setfingers(p,values):
 for n in finger:p[n]=p[parent[n]]@lr[n]@values[n]
def refroot(kind,f):
 samples=ref[kind]['samples'];lo=int(f);hi=min(lo+1,int(ref[kind]['range'][1]));return mix(Matrix(samples[str(lo)]['WPN_root']),Matrix(samples[str(hi)]['WPN_root']),f-lo)
def scaledrotation(q,weight,limit):
 if q.w<0:q.negate()
 return Quaternion().slerp(q,min(weight,math.radians(limit)/max(q.angle,1e-6)))
def handling(kind,f):
 # The reference's complete root motion supplies the asymmetric lean and recovery.
 charging=kind=='equip_charge' or (kind=='reload_empty' and f>=126)
 if charging:
  cf=f if kind=='equip_charge' else f-126
  active=smooth(cf/9)*(1-smooth((cf-25)/13))
  q=(refroot('equip_charge',38).inverted()@refroot('equip_charge',cf)).to_quaternion()
  roll=Quaternion((0,1,0),math.radians(-22)*active)
  q=scaledrotation(q,.70*active,24)@roll
  # Pull stop and handle return each have one short impulse, no periodic shake.
  pull=math.exp(-((cf-16)/1.2)**2);release=math.exp(-((cf-25)/.9)**2)
  offset=(.008*active,.008*active+.005*pull-.003*release,-.009*active-.002*release)
  return Matrix.Translation(offset)@q.to_matrix().to_4x4()
 rf=min(f,126);active=smooth(rf/14)*(1-smooth((rf-102)/24))
 q=(refroot('reload',126).inverted()@refroot('reload',rf)).to_quaternion()
 q=scaledrotation(q,.38*active,16)
 throw=math.exp(-((rf-31)/5.)**2);seat=math.exp(-((rf-95)/1.4)**2);settle=math.exp(-((rf-99)/2.)**2)
 q=q@Quaternion((0,1,0),math.radians(-7)*throw+math.radians(1.2)*seat)
 return Matrix.Translation((-.007*throw,.007*throw,-.0045*seat+.0015*settle))@q.to_matrix().to_4x4()
grasp={n:Matrix(v) for n,v in inputs['donor']['fingers'].items()};G=Matrix(models['parts']['drum']['grasp_in_mag']);meta={}
for family in ['base','vertical','canted','prism','angled']:
 for kind,end in [('reload',126),('reload_empty',164),('equip_charge',38),('drum_reload',126),('drum_reload_empty',164)]:
  basekind=kind.removeprefix('drum_');drum=kind.startswith('drum_');original=bpy.data.actions['QBZ191_Contact_'+family+'_'+basekind]
  start=pose(original,0);held=start['WPN_root'].inverted()@start['hand_l'];heldB={n:basis(start,n) for n in finger}
  magH=start['WPN_root'].inverted()@start['WPN_SOCKET_Magazine']@G
  pickup=pose(original,49) if drum else start;pickupH=pickup['WPN_root'].inverted()@pickup['WPN_SOCKET_Magazine']@G
  released=pose(original,36) if drum else start;releaseH=released['WPN_root'].inverted()@released['WPN_SOCKET_Magazine']@G
  samples=[];previous={}
  for k in range(end*4+1):
   f=k*.25;p=pose(original,f);W=p['WPN_root']
   if drum and f<126:
    if f<16:H=W@track([(0,held),(5,shift(held,(.012,0,-.01))),(12,shift(magH,(.015,0,-.008))),(16,magH)],f)
    elif f<=36:H=p['WPN_SOCKET_Magazine']@G
    elif f<49:H=W@track([(36,releaseH),(42,shift(pickupH,(.025,.04,-.025))),(49,pickupH)],f)
    elif f<=98:H=p['WPN_SOCKET_Magazine']@G
    else:H=W@track([(98,magH),(105,shift(magH,(.105,.01,-.008))),(117,shift(held,(.04,.02,-.015))),(126,held)],f)
    if f<16:fb={n:mix(heldB[n],grasp[n],smooth(f/16)) for n in finger}
    elif f<=36 or 49<=f<=98:fb=grasp
    elif f<49:
     openness=1-.6*math.sin(math.pi*(f-36)/13)**2;fb={}
     for n in finger:
      loc,q,sc=grasp[n].decompose();fb[n]=Matrix.LocRotScale(loc,Quaternion().slerp(q,openness),sc)
    else:
     fb={};a=smooth((f-98)/7);b=smooth((f-110)/16)
     for n in finger:
      loc,q,sc=grasp[n].decompose();opened=Matrix.LocRotScale(loc,Quaternion().slerp(q,.38),sc);fb[n]=mix(mix(grasp[n],opened,a),heldB[n],b)
    solve_arm(p,rest,H,W,.65*smooth(f/12)*(1-smooth((f-111)/15)));setfingers(p,fb)
   # A single rigid delta moves the weapon and complete arms together. It cannot
   # displace the corrected magazine/handle grip or add frame-dependent IK jitter.
   delta=W@handling(basekind,f)@W.inverted()
   p={n:delta@m for n,m in p.items()};row={}
   for n in names:
    loc,q,sc=basis(p,n).decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();row[n]=(loc,q,sc)
   samples.append(row)
  a=bpy.data.actions.new('QBZ191_Handling_'+family+'_'+kind);a.use_fake_user=True;r.animation_data.action=a
  for n in names:
   b=r.pose.bones[n];b.rotation_mode='QUATERNION'
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
  curves={(c.data_path,c.array_index):c for c in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves}
  for n in names:
   for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(count):
     curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(samples));curve.keyframe_points.foreach_set('co',[v for k,row in enumerate(samples) for v in (k*.25,row[n][field][axis])])
     for key in curve.keyframe_points:key.interpolation='LINEAR'
     curve.update()
  r.animation_data.action_slot=a.slots[0];s.frame_start=0;s.frame_end=end;s.render.fps=60;s.frame_set(0)
  bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  name='A_QBZ191_'+('' if family=='base' else family+'_')+kind;dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True);file=dest/(name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.25,bake_anim_simplify_factor=0)
  meta[family+':'+kind]={'name':name,'family':family,'file':str(file),'sample_rate':240,'duration':end/60,'action':a.name}
  (O/'animations.json').write_text(json.dumps(meta,indent=2));print('QBZ_HANDLING_EXPORTED',family,kind,flush=True)
pose(bpy.data.actions['QBZ191_base_idle'],0);s.frame_end=164
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Attachments_Editable.blend'));print('QBZ_HANDLING_AUTHORING_COMPLETE',flush=True)
